import os
import shutil

from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from cats.models import Cat, Photo
from cats.schemas import CatCreate, PhotoCreate, CatUpdate
from sqlalchemy.ext.asyncio import AsyncSession


async def create_cat(db: AsyncSession, cat: CatCreate):
    db_cat = Cat(**cat.dict())
    db.add(db_cat)
    await db.commit()
    await db.refresh(db_cat)
    return db_cat


async def create_photo(db: AsyncSession, photo: PhotoCreate):
    db_photo = Photo(**photo.dict())
    db.add(db_photo)
    await db.commit()
    await db.refresh(db_photo)
    return db_photo


async def get_cat(db: AsyncSession, cat_id: int):
    result = await db.execute(select(Cat).filter(Cat.id == cat_id))
    return result.scalars().first()


async def get_cats(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Cat).offset(skip).limit(limit))
    return result.scalars().all()


async def get_cat_with_photos(db: AsyncSession, cat_id: int):
    result = await db.execute(select(Cat).options(selectinload(Cat.photos)).filter(Cat.id == cat_id))
    return result.scalars().first()


async def delete_cat(db: AsyncSession, cat: Cat):
    photo_dir = os.path.join("uploads/photo_cats", f"{cat.id}_{cat.name}")
    if os.path.exists(photo_dir):
        shutil.rmtree(photo_dir)

    subquery = delete(Photo).where(Photo.cat_id == cat.id)
    await db.execute(subquery)

    await db.delete(cat)
    await db.commit()

    return cat


async def update_cat(db: AsyncSession, db_cat: Cat, cat_update: CatUpdate):
    update_data = cat_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_cat, key, value)

    await db.commit()
    await db.refresh(db_cat)

    return db_cat
