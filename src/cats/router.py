import os
import shutil
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from cats.schemas import Cat, CatCreate, CatWithPhotos, PhotoCreate, CatUpdate
from cats.service import (create_cat, create_photo, get_cat,
                          get_cat_with_photos, get_cats, delete_cat, update_cat)
from database import SessionLocal as Session
from database import get_db

router = APIRouter(prefix="/cats", tags=["Cats"])


# @router.post("/photos/", response_model=Photo)
# def create_photo_view(photo: PhotoCreate, db: Session = Depends(get_db)):
#     return create_photo(db, photo)


@router.get("/all/", response_model=list[Cat])
def read_cats_view(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    cats = get_cats(db, skip=skip, limit=limit)
    return cats


@router.get("/{cat_id}/", response_model=Cat)
def read_cat_id(cat_id: int, db: Session = Depends(get_db)):
    cat = get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    return cat


@router.get("/{cat_id}/photos/", response_model=CatWithPhotos)
def read_cat_view(cat_id: int, db: Session = Depends(get_db)):
    cat = get_cat_with_photos(db, cat_id=cat_id)
    return cat


@router.post("/", response_model=Cat)
def create_cat_view(cat: CatCreate, db: Session = Depends(get_db)):
    return create_cat(db, cat)


@router.post("/{cat_id}/photos/")
def upload_cat_photos_view(cat_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    cat = get_cat(db, cat_id=cat_id)
    if not cat:
        return {"detail": "Cat not found"}
    for file in files:
        photo = PhotoCreate(url=file.filename, cat_id=cat_id)
        create_photo(db, photo)

        if not os.path.exists(f"uploads/photo_cats/{cat_id}_{cat.name}/"):
            os.makedirs(f"uploads/photo_cats/{cat_id}_{cat.name}/")

        with open(f"uploads/photo_cats/{cat_id}_{cat.name}/{file.filename}", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    return {"detail": "Photos uploaded successfully"}


@router.delete("/{cat_id}")
def delete_cat_id(cat_id: int, db: Session = Depends(get_db)):
    cat = get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    delete_cat(db, cat)
    return {"message": f"Cat with id: {cat_id} and all related photos deleted successfully"}


@router.put("/{cat_id}", response_model=Cat)
def update_cat_view(cat_id: int, cat_update: CatUpdate, db: Session = Depends(get_db)):
    db_cat = get_cat(db, cat_id=cat_id)
    if not db_cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    db_cat = update_cat(db, db_cat, cat_update)
    return db_cat
