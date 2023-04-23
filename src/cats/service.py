from sqlalchemy.orm import selectinload

from cats.models import Cat, Photo
from cats.schemas import CatCreate, PhotoCreate, CatUpdate
from database import SessionLocal as Session


def create_cat(db: Session, cat: CatCreate):
    db_cat = Cat(**cat.dict())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat


def create_photo(db: Session, photo: PhotoCreate):
    db_photo = Photo(**photo.dict())
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return db_photo


def get_cat(db: Session, cat_id: int):
    return db.query(Cat).filter(Cat.id == cat_id).first()


def get_cats(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Cat).offset(skip).limit(limit).all()


def get_cat_with_photos(db: Session, cat_id: int):
    return db.query(Cat).filter(Cat.id == cat_id).options(selectinload(Cat.photos)).first()


def delete_cat(db: Session, cat: Cat):
    for photo in cat.photos:
        db.delete(photo)

    db.delete(cat)
    db.commit()

    return cat


def update_cat(db: Session, db_cat: Cat, cat_update: CatUpdate):
    update_data = cat_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_cat, key, value)

    db.commit()
    db.refresh(db_cat)

    return db_cat
