import os
import shutil
from typing import List

from fastapi import UploadFile
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from cats.models import Cat, Photo
from cats.schemas import CatCreate, CatUpdate, PhotoCreate


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


async def create_cat_with_photos(
        db: AsyncSession, cat: CatCreate, files: List[UploadFile]
) -> Cat:
    """
    Save the cat and all his photos in the database.
    Also save photos locally in the specified folder 'photo_dir'
    using save_photo_to_directory method.
    """

    db_cat = Cat(**cat.dict())
    db.add(db_cat)
    await db.flush()

    for file in files:
        photo = PhotoCreate(url=file.filename, cat_id=db_cat.id)
        db_photo = Photo(**photo.dict())
        db.add(db_photo)
        await db.flush()

        photo_dir = os.path.join("uploads/photo_cats", f"{db_cat.id}_{db_cat.name}")
        await save_photo_to_directory(file, photo_dir)

    await db.commit()
    await db.refresh(db_cat)
    return db_cat


async def create_cat(db: AsyncSession, cat: CatCreate):
    """
    Saving a cat without its photos in the database.
    """
    db_cat = Cat(**cat.dict())
    db.add(db_cat)
    await db.commit()
    await db.refresh(db_cat)
    return db_cat


async def create_cat_photos(
        db: AsyncSession, photo: PhotoCreate, file: UploadFile, cat: Cat
):
    """
    We add both locally and to the database the added photos of the cat
    """
    db_photo = Photo(**photo.dict())
    db.add(db_photo)
    await db.commit()
    await db.refresh(db_photo)

    photo_dir = os.path.join("uploads/photo_cats", f"{cat.id}_{cat.name}")
    await save_photo_to_directory(file, photo_dir)

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

    with open(os.path.join(directory, file.filename), "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
