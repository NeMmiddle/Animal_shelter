import io
import pickle
from typing import List, Tuple

from fastapi import UploadFile, HTTPException
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


async def get_user_credentials() -> Credentials:
    """
    Gets the user credentials for Google Drive API.
    """
    try:
        # Load the saved credentials from file
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    except FileNotFoundError:
        # Create a flow instance to manage the OAuth2.0 Authorization Grant Flow steps.
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", scopes=SCOPES
        )

        # Run the flow to authorize this app and get the user credentials.
        creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return creds


async def upload_photos_to_google_drive(
    files: List[UploadFile], cat_id: int, cat_name: str
) -> Tuple[List[str], str]:
    """
    Upload photos to Google Drive and return their URLs and the ID of the cat's folder.
    """
    # Check file types
    allowed_extensions = (".jpg", ".jpeg", ".png", ".gif")
    for file in files:
        if not file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' has an invalid file type."
                f"Only image files are allowed.",
            )

    # Authorize with Google Drive API
    creds = await get_user_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    # Check if the "Photos of cats" folder exists, create it if necessary
    query = "mimeType='application/vnd.google-apps.folder' and name='Photos of cats'"
    folder = (
        drive_service.files().list(q=query, fields="files(id)").execute().get("files")
    )
    if not folder:
        folder_metadata = {
            "name": "Photos of cats",
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = (
            drive_service.files().create(body=folder_metadata, fields="id").execute()
        )
        google_folder_id = folder.get("id")
    else:
        google_folder_id = folder[0].get("id")

    # Check if the cat's folder exists, create it if necessary
    query = f"mimeType='application/vnd.google-apps.folder' and name='{cat_id} - {cat_name}' and parents='{google_folder_id}'"
    folder = (
        drive_service.files().list(q=query, fields="files(id)").execute().get("files")
    )
    if not folder:
        folder_metadata = {
            "name": f"{cat_id} - {cat_name}",
            "parents": [google_folder_id],
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = (
            drive_service.files().create(body=folder_metadata, fields="id").execute()
        )
        google_folder_id = folder.get("id")
    else:
        google_folder_id = folder[0].get("id")

    # Upload photos to the cat's folder
    urls = []
    for file in files:
        media = MediaIoBaseUpload(
            io.BytesIO(await file.read()), mimetype=file.content_type, resumable=True
        )
        file_metadata = {"name": file.filename, "parents": [google_folder_id]}
        file = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        url = f"https://drive.google.com/uc?id={file.get('id')}"
        urls.append(url)

    return urls, google_folder_id


async def delete_photos_from_drive(cat_id: int, cat_name: str) -> None:
    """
    Delete photos of the cat from Google Drive using Google Drive API.
    """
    try:
        # Authorize with Google Drive API
        creds = await get_user_credentials()
        if creds is None:
            raise HTTPException(status_code=401, detail="Authorization required")
        drive_service = build("drive", "v3", credentials=creds)

        # Find the folder with the cat's photos
        query = f"mimeType='application/vnd.google-apps.folder' and name='{cat_id} - {cat_name}'"
        folder = (
            drive_service.files()
            .list(q=query, fields="files(id)")
            .execute()
            .get("files")
        )
        if not folder:
            raise HTTPException(
                status_code=404, detail=f"Folder for cat with id={cat_id} not found"
            )
        google_folder_id = folder[0].get("id")

        # Delete all files in the folder
        query = f"'{google_folder_id}' in parents"
        files = (
            drive_service.files()
            .list(q=query, fields="files(id)")
            .execute()
            .get("files", [])
        )
        for file in files:
            drive_service.files().delete(fileId=file.get("id")).execute()

        # Delete the folder
        drive_service.files().delete(fileId=google_folder_id).execute()
    except HttpError as e:
        if e.resp.status == 401:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        elif e.resp.status == 404:
            raise HTTPException(
                status_code=404, detail=f"Folder for cat with id={cat_id} not found"
            )
        else:
            raise HTTPException(
                status_code=500, detail="Failed to delete photos from Google Drive"
            )
    except Exception:
        raise HTTPException(
            status_code=500, detail="Failed to delete photos from Google Drive"
        )
