import os
import shutil
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from cats.models import Cat, Photo
from cats.schemas import CatCreate, CatUpdate, PhotoCreate
from cats.utils import upload_photos_to_google_drive, delete_photos_from_drive


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
        db_cat = Cat(name=cat.name, age=cat.age, gender=cat.gender, about=cat.about, sterilized=cat.sterilized)
        db.add(db_cat)
        await db.flush()

        if files is not None:
            # Upload photos to Google Drive and create records in the database
            try:
                # Upload photos to Google Drive
                urls, folder_id = await upload_photos_to_google_drive(files, db_cat.id, db_cat.name)

                # Create a record of the photo in the database
                for url in urls:
                    photo = PhotoCreate(url=url, cat_id=db_cat.id, folder_id=folder_id)
                    db_photo = Photo(**photo.dict())
                    db.add(db_photo)
                    await db.flush()
            except Exception as e:
                # If there is an error during photo upload, delete the cat record from the database
                await db.delete(db_cat)
                await db.flush()
                raise e

        # Save the folder_id to the database
        db_cat.folder_id = folder_id

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


async def delete_cat(db: AsyncSession, cat_id: int) -> None:
    """
    Delete the cat and all his photos from the database.
    """
    try:
        # Get the cat from the database
        db_cat = await db.get(Cat, cat_id)
        if db_cat is None:
            raise HTTPException(status_code=404, detail=f"Cat with id={cat_id} not found")

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


async def save_photo_to_directory(file: UploadFile, directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, file.filename)
    if os.path.exists(file_path):
        shutil.rmtree(directory)  # удаляем всю папку и ее содержимое

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file.file.close()
