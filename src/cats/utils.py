import io
import pickle
from typing import List

from fastapi import UploadFile, HTTPException
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']


async def get_user_credentials() -> Credentials:
    """
    Gets the user credentials for Google Drive API.
    """
    try:
        # Load the saved credentials from file
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    except FileNotFoundError:
        # Create a flow instance to manage the OAuth2.0 Authorization Grant Flow steps.
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secret.json', scopes=SCOPES)

        # Run the flow to authorize this app and get the user credentials.
        creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


async def upload_photos_to_google_drive(files: List[UploadFile], cat_id: int, cat_name: str) -> List[str]:
    """
    Upload photos to Google Drive and return their URLs.
    """
    # Check file types
    allowed_extensions = ('.jpg', '.jpeg', '.png', '.gif')
    for file in files:
        if not file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(status_code=400,
                                detail=f"File '{file.filename}' has an invalid file type."
                                f"Only image files are allowed.")

    # Authorize with Google Drive API
    creds = await get_user_credentials()
    drive_service = build('drive', 'v3', credentials=creds)

    # Check if the "Photos of cats" folder exists, create it if necessary
    query = "mimeType='application/vnd.google-apps.folder' and name='Photos of cats'"
    folder = drive_service.files().list(q=query, fields='files(id)').execute().get('files')
    if not folder:
        folder_metadata = {
            'name': 'Photos of cats',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')
    else:
        folder_id = folder[0].get('id')

    # Create a folder for the cat's photos in the "Photos of cats" folder
    folder_metadata = {
        'name': f'{cat_id} - {cat_name}',
        'parents': [folder_id],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    folder_id = folder.get('id')

    # Upload photos to the cat's folder
    urls = []
    for file in files:
        media = MediaIoBaseUpload(io.BytesIO(await file.read()), mimetype=file.content_type, resumable=True)
        file_metadata = {
            'name': file.filename,
            'parents': [folder_id]
        }
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        url = f"https://drive.google.com/uc?id={file.get('id')}"
        urls.append(url)

    return urls
