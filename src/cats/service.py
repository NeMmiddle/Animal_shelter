import os
import shutil
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from cats.models import Cat, Photo
from cats.schemas import CatCreate, CatUpdate, PhotoCreate
from cats.utils import upload_photos_to_google_drive


async def get_cats(db: AsyncSession, skip: int, limit: int):
    """
    Get all the added cats from the database.
    """
    result = await db.execute(select(Cat).offset(skip).limit(limit))
    return result.scalars().all()


async def get_cat(db: AsyncSession, cat_id: int):
    """
    Get one cat for him id.
    """
    result = await db.execute(select(Cat).filter(Cat.id == cat_id))
    return result.scalars().first()


async def get_cat_with_photos(db: AsyncSession, cat_id: int):
    """
    Get the added cat and all his photos from the database.
    """
    result = await db.execute(
        select(Cat).options(selectinload(Cat.photos)).filter(Cat.id == cat_id)
    )
    return result.scalars().first()


async def create_cat_with_photos(db: AsyncSession, cat: CatCreate, files: Optional[List[UploadFile]]) -> Cat:
    """
    Save the cat and all his photos in the database.
    Also save photos on Google Drive using Google Drive API.
    """

    try:
        # Create a record of the cat in the database
        db_cat = Cat(**cat.dict())
        db.add(db_cat)
        await db.flush()

        if files is not None:
            # Upload photos to Google Drive and create records in the database
            try:
                # Upload photos to Google Drive
                urls = await upload_photos_to_google_drive(files, db_cat.id, db_cat.name)

                # Create a record of the photo in the database
                for url in urls:
                    photo = PhotoCreate(url=url, cat_id=db_cat.id)
                    db_photo = Photo(**photo.dict())
                    db.add(db_photo)
                    await db.flush()
            except Exception as e:
                # If there is an error during photo upload, delete the cat record from the database
                await db.delete(db_cat)
                await db.flush()
                raise e

        await db.commit()
        await db.refresh(db_cat)
        return db_cat
    except Exception as e:
        # If there is an error during cat creation, rollback the database transaction
        await db.rollback()
        raise e


async def create_cat_photos(
        db: AsyncSession, photo: PhotoCreate, file: UploadFile, cat: Cat
):
    """
    Add both locally and to the database the added photos of the cat
    """
    db_photo = Photo(**photo.dict())
    db.add(db_photo)
    await db.commit()
    await db.refresh(db_photo)

    return db_photo


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


async def delete_cat(db: AsyncSession, cat: Cat):
    """
    Delete the cat locally and from the database
    """
    photo_dir = os.path.join("uploads/photo_cats", f"{cat.id}_{cat.name}")
    if os.path.exists(photo_dir):
        shutil.rmtree(photo_dir)

    subquery = delete(Photo).where(Photo.cat_id == cat.id)
    await db.execute(subquery)

    await db.delete(cat)
    await db.commit()

    return cat


async def save_photo_to_directory(file: UploadFile, directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, file.filename)
    if os.path.exists(file_path):
        shutil.rmtree(directory)  # удаляем всю папку и ее содержимое

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file.file.close()
