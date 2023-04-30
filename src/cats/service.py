from typing import List, Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from cats.models import Cat, Photo
from cats.schemas import CatCreate, CatUpdate, PhotoCreate, CatWithPhotos
from cats.utils import upload_photos_to_google_drive, delete_photos_from_drive


async def get_cat(db: AsyncSession, cat_id: int) -> Cat:
    """
    Get one cat by id along with their photos.
    """
    try:
        result = await db.execute(
            select(Cat).options(selectinload(Cat.photos)).filter(Cat.id == cat_id)
        )
        return result.scalars().first()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def get_cats(db: AsyncSession, skip: int = 0, limit: int = 20) -> [CatWithPhotos]:
    """
    Get all the added cats from the database along with their photos.
    """
    try:
        result = await db.execute(
            select(Cat).options(selectinload(Cat.photos)).offset(skip).limit(limit)
        )
        return result.scalars().all()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def get_cat_with_photos(db: AsyncSession, cat_id: int) -> CatWithPhotos:
    """
    Get the added cat and all his photos from the database.
    """
    try:
        result = await db.execute(
            select(Cat).options(selectinload(Cat.photos)).filter(Cat.id == cat_id)
        )
        return result.scalars().first()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


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
        # Upload photos to Google Drive
        urls, folder_id = await upload_photos_to_google_drive(
            files=files, cat_id=cat_id, cat_name=cat_name
        )

        # Create records of the photos in the database
        for url in urls:
            photo = PhotoCreate(url=url, cat_id=cat_id, google_folder_id=folder_id)
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
    Save the cat and all his photos in the database.
    Also save photos on Google Drive using Google Drive API.
    """
    try:
        # Create a record of the cat in the database
        db_cat = await create_cat(db, cat)

        if files:
            # Upload photos to Google Drive and create records in the database
            urls, folder_id = await upload_photos(db, files, db_cat.id, db_cat.name)

            # Save the folder ID to the database
            db_cat.google_folder_id = folder_id

        await db.commit()
        await db.refresh(db_cat)
    except Exception as e:
        # If there is an error during cat creation or photo upload, rollback the database transaction
        await db.rollback()
        raise e


async def create_cat_photos(db: AsyncSession, files: List[UploadFile], cat_id: int):
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
        photo = PhotoCreate(url=url, google_folder_id=google_folder_id, cat_id=cat.id)
        db_photo = Photo(**photo.dict())
        db.add(db_photo)
        await db.flush()

    # Save google_folder_id in the database
    cat.google_folder_id = google_folder_id
    await db.commit()


async def update_cat(db: AsyncSession, db_cat: Cat, cat_update: CatUpdate):
    """
    Update information about the cat by its id and save it in the database
    """
    update_data = cat_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_cat, key, value)

    await db.commit()
    await db.refresh(db_cat)

    return db_cat


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
