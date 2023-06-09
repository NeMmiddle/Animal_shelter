from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from cats.models import Cat, CatPhoto
from cats.schemas import CatCreate, CatUpdate, CatWithPhotos, PhotoCreate, Photo
from cats.utils import (delete_google_drive_file, delete_photos_from_drive,
                        update_google_folder_name,
                        upload_photos_to_google_drive)


async def get_cat(db: AsyncSession, cat_id: int) -> [CatWithPhotos]:
    """
    Get one cat by id along with their photos.
    """
    query = await db.execute(
        select(Cat).options(selectinload(Cat.photos)).filter(Cat.id == cat_id)
    )
    cat = query.scalars().first()
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cat not found"
        )
    return cat


async def get_photo(db: AsyncSession, photo_id: int) -> [Photo]:
    """
    Get a photo from the database by ID.
    """
    result = await db.execute(select(CatPhoto).where(CatPhoto.id == photo_id))
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
    cats = query.scalars().all()
    return cats


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
            db_photo = CatPhoto(**photo.dict())
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
        await db.rollback()
        raise e


async def add_photos_for_the_cat(
    db: AsyncSession, files: List[UploadFile], cat_id: int
) -> None:
    """
    Add the added photos of the cat to the database and upload them to Google Drive.
    """
    try:
        # Get the cat from the database
        cat = await get_cat(db, cat_id=cat_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Cat not found")

        # Upload photos to Google Drive and get google_folder_id
        urls, google_folder_id = await upload_photos_to_google_drive(
            files, cat_id=cat_id, cat_name=cat.name
        )

        # Create records of the photos in the database
        photos = []
        for url in urls:
            photo = PhotoCreate(
                url=url, google_file_id=url.split("=")[1], cat_id=cat.id
            )
            db_photo = CatPhoto(**photo.dict())
            photos.append(db_photo)

        # Add all the photos to the database at once
        db.add_all(photos)
        await db.commit()

        # Save google_folder_id in the database
        cat.google_folder_id = google_folder_id
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise e


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
        photos = await db.execute(select(CatPhoto).where(CatPhoto.cat_id == cat_id))
        for photo in photos.scalars():
            await db.delete(photo)

        # Delete the cat record from the database
        await db.delete(db_cat)

        # Delete the cat's photos from Google Drive
        await delete_photos_from_drive(cat_id, db_cat.name)

        await db.commit()

    except Exception as e:
        await db.rollback()
        raise e


async def update_cat_in_db(
    db: AsyncSession, db_cat: CatWithPhotos, cat_update: CatUpdate
) -> CatWithPhotos:
    """
    Update information about the cat by its id
    and save it in the database and in Google Drive
    """
    update_data = cat_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cat, key, value)

    await db.commit()
    await db.refresh(db_cat)

    return db_cat


async def update_cat(
    db: AsyncSession, cat_id: int, cat_update: CatUpdate
) -> CatWithPhotos:
    """
    Update information about the cat, if the name changes,
    the name will be updated on Google Drive.
    """
    try:
        db_cat = await get_cat(db, cat_id=cat_id)
        if not db_cat:
            raise HTTPException(status_code=404, detail="Cat not found")

        # Update the cat's information in the database
        db_cat = await update_cat_in_db(db, db_cat, cat_update)

        # Update the name of the photos folder in Google Drive
        folder_id = db_cat.google_folder_id
        folder_name = db_cat.name

        updated_folder = await update_google_folder_name(
            folder_id=folder_id, cat_id=cat_id, new_name=folder_name
        )
        if not updated_folder:
            raise HTTPException(
                status_code=500,
                detail="Failed to update the name of the photos folder in Google Drive",
            )

        await db.commit()

        return db_cat

    except Exception as e:
        await db.rollback()
        raise e


async def delete_photo(db: AsyncSession, photo_id: int, cat_id: int) -> None:
    """
    Delete a photo from the database by ID.
    """

    try:
        # Get the cat and the photo from the database
        cat = await get_cat(db, cat_id)
        photo = await get_photo(db, photo_id)

        # Check if the cat and the photo exist and if the photo belongs to the cat
        if not cat:
            raise HTTPException(status_code=404, detail="Cat not found")
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        if photo.cat_id != cat.id:
            raise HTTPException(
                status_code=400, detail="Photo does not belong to the cat"
            )

        # Delete the photo from Google Drive if it exists
        if photo.google_file_id:
            await delete_google_drive_file(file_id=photo.google_file_id)

        # Delete the photo from the database
        await db.delete(photo)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise e
