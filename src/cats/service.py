from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from cats.models import Cat, Photo
from cats.schemas import CatCreate, CatUpdate, CatWithPhotos, PhotoCreate
from cats.utils import (
    delete_google_drive_file,
    delete_photos_from_drive,
    update_folder_name,
    upload_photos_to_google_drive,
)


async def get_cat(db: AsyncSession, cat_id: int) -> [CatWithPhotos]:
    """
    Get one cat by id along with their photos.
    """
    query = await db.execute(
        select(Cat).options(selectinload(Cat.photos)).filter(Cat.id == cat_id)
    )
    result = query.scalars().first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cat not found"
        )
    return result


async def get_photo(db: AsyncSession, photo_id: int) -> [Photo]:
    """
    Get a photo from the database by ID.
    """
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found"
        )
    return photo


async def get_cats(db: AsyncSession, skip: int = 0, limit: int = 20) -> [CatWithPhotos]:
    """
    Get all the added cats from the database along with their photos.
    """
    query = await db.execute(
        select(Cat).options(selectinload(Cat.photos)).offset(skip).limit(limit)
    )
    result = query.scalars().all()
    return result


async def create_cat(db: AsyncSession, cat: CatCreate) -> Cat:
    """
    Create a record of the cat in the database.
    """
    try:
        db_cat = Cat(
            name=cat.name,
            age=cat.age,
            gender=cat.gender,
            about=cat.about,
            sterilized=cat.sterilized,
        )
        db.add(db_cat)
        await db.flush()
        return db_cat
    except Exception as e:
        await db.rollback()
        raise e


async def upload_photos(
    db: AsyncSession, files: List[UploadFile], cat_id: int, cat_name: str
) -> Tuple[List[str], str]:
    """
    Upload photos to Google Drive and return their URLs and folder ID.
    """
    try:
        # Check maximum number of photos
        if len(files) > 10:
            raise ValueError("Maximum number of photos exceeded.")

        # Check maximum photo size
        for file in files:
            if file.content_type.startswith("image/") and file.size > 5 * 1024 * 1024:
                raise ValueError("Maximum photo size exceeded.")

        # Check file types
        allowed_extensions = (".jpg", ".jpeg", ".png", ".gif")
        for file in files:
            if not file.filename.lower().endswith(allowed_extensions):
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' has an invalid file type."
                    f"Only image files are allowed.",
                )
        # Upload photos to Google Drive
        urls, folder_id = await upload_photos_to_google_drive(
            files=files, cat_id=cat_id, cat_name=cat_name
        )

        # Check if photos were uploaded successfully
        if not urls or not folder_id:
            raise ValueError("Unable to upload photos to Google Drive.")

        # Create records of the photos in the database
        for url in urls:
            photo = PhotoCreate(
                url=url, cat_id=cat_id, google_file_id=url.split("=")[1]
            )
            db_photo = Photo(**photo.dict())
            db.add(db_photo)
            await db.flush()

        return urls, folder_id
    except Exception as e:
        await db.rollback()
        raise e


async def create_cat_with_photos(
    db: AsyncSession, cat: CatCreate, files: Optional[List[UploadFile]] = None
) -> None:
    """
    Create a new cat with photos and save them in the database and on Google Drive.
    """
    try:
        # Create a record of the cat in the database
        db_cat = await create_cat(db, cat)

        if files:
            # Upload photos to Google Drive and create records in the database
            urls, folder_id = await upload_photos(db, files, db_cat.id, db_cat.name)

            db_cat.google_folder_id = folder_id

        await db.commit()
        await db.refresh(db_cat)
    except Exception as e:
        # If there is an error during cat creation or photo upload, rollback the database transaction
        await db.rollback()
        raise e


async def add_photos_for_the_cat(
    db: AsyncSession, files: List[UploadFile], cat_id: int
):
    """
    Add the added photos of the cat to the database and upload them to Google Drive
    """

    # Get the cat from the database
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")

    # Upload photos to Google Drive and get google_folder_id
    urls, google_folder_id = await upload_photos_to_google_drive(
        files, cat_id=cat_id, cat_name=cat.name
    )

    # Create records of the photos in the database
    for url in urls:
        photo = PhotoCreate(url=url, google_file_id=url.split("=")[1], cat_id=cat.id)
        db_photo = Photo(**photo.dict())
        db.add(db_photo)
        await db.flush()

    # Save google_folder_id in the database
    cat.google_folder_id = google_folder_id
    await db.commit()


async def delete_cat(db: AsyncSession, cat_id: int) -> None:
    """
    Delete the cat and all his photos from the database.
    """
    try:
        # Get the cat from the database
        db_cat = await db.get(Cat, cat_id)
        if db_cat is None:
            raise HTTPException(
                status_code=404, detail=f"Cat with id={cat_id} not found"
            )

        # Delete all photos of the cat from the database
        photos = await db.execute(select(Photo).where(Photo.cat_id == cat_id))
        for photo in photos.scalars():
            await db.delete(photo)

        # Delete the cat record from the database
        await db.delete(db_cat)

        # Delete the cat's photos from Google Drive
        await delete_photos_from_drive(cat_id, db_cat.name)

        await db.commit()
    except Exception as e:
        # If there is an error during cat deletion, rollback the database transaction
        await db.rollback()
        raise e


async def update_cat_in_db(
    db: AsyncSession, db_cat: CatWithPhotos, cat_update: CatUpdate
):
    """
    Update information about the cat by its id and save it in the database and in Google Drive
    """
    update_data = cat_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cat, key, value)

    await db.commit()
    await db.refresh(db_cat)

    return db_cat


async def update_cat(db: AsyncSession, cat_id: int, cat_update: CatUpdate):
    try:
        db_cat = await get_cat(db, cat_id=cat_id)
        if not db_cat:
            raise HTTPException(status_code=404, detail="Cat not found")

        # Update the cat's information in the database
        db_cat = await update_cat_in_db(db, db_cat, cat_update)

        # Update the name of the photos folder in Google Drive
        folder_id = db_cat.google_folder_id  # ID of the folder in Google Drive
        folder_name = db_cat.name  # New name of the folder

        updated_folder = await update_folder_name(
            folder_id=folder_id, cat_id=cat_id, new_name=folder_name
        )
        if not updated_folder:
            raise HTTPException(
                status_code=500,
                detail="Failed to update the name of the photos folder in Google Drive",
            )

        # Commit the transaction to the database
        await db.commit()

        return db_cat

    except Exception as e:
        # Rollback the transaction if an error occurs
        await db.rollback()
        raise e


async def get_cat_and_photo(
    db: AsyncSession, cat_id: int, photo_id: int
) -> Tuple[Optional[Cat], Optional[Photo]]:
    """
    Get a cat and a photo from the database by their IDs.
    """
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        return None, None

    photo = await get_photo(db, photo_id=photo_id)
    if not photo:
        return cat, None

    return cat, photo


async def delete_photo_from_db(db: AsyncSession, photo: Photo):
    """
    Delete a photo from the database.
    """
    try:
        await db.delete(photo)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"An error occurred while deleting the photo: {e}"
        )


async def delete_photo(db: AsyncSession, photo_id: int) -> Optional[Photo]:
    """
    Delete a photo from the database by ID.
    """
    photo = await get_photo(db, photo_id=photo_id)
    if not photo:
        return None

    if photo.google_file_id:
        await delete_google_drive_file(file_id=photo.google_file_id)

    await delete_photo_from_db(db=db, photo=photo)

    return photo
