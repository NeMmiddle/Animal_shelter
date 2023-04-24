import os
import shutil
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from cats.schemas import Cat, CatCreate, CatWithPhotos, PhotoCreate, CatUpdate
from cats.service import (create_cat, create_photo, get_cat,
                          get_cat_with_photos, get_cats, delete_cat, update_cat)
from database import get_db

router = APIRouter(prefix="/cats", tags=["Cats"])


@router.get("/all/", response_model=list[Cat])
async def get_all_cats(skip: int = 0, limit: int = 100, db=Depends(get_db)):
    cats = await get_cats(db, skip=skip, limit=limit)
    return cats


@router.get("/{cat_id}/", response_model=Cat)
async def get_cat_by_id(cat_id: int, db=Depends(get_db)):
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    return cat


@router.get("/{cat_id}/photos/", response_model=CatWithPhotos)
async def get_cat_photos(cat_id: int, db=Depends(get_db)):
    cat = await get_cat_with_photos(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    return cat


@router.post("/", response_model=Cat)
async def create_cat_record(cat: CatCreate, db=Depends(get_db)):
    return await create_cat(db, cat)


@router.post("/{cat_id}/photos/")
async def upload_cat_photos(cat_id: int, files: List[UploadFile] = File(...), db=Depends(get_db)):
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    for file in files:
        photo = PhotoCreate(url=file.filename, cat_id=cat_id)
        await create_photo(db, photo)

        photo_dir = os.path.join("uploads/photo_cats", f"{cat_id}_{cat.name}")
        if not os.path.exists(photo_dir):
            os.makedirs(photo_dir)

        with open(os.path.join(photo_dir, file.filename), "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    return {"detail": "Photos uploaded successfully"}


@router.delete("/{cat_id}")
async def delete_cat_by_id(cat_id: int, db=Depends(get_db)):
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    await delete_cat(db, cat)
    return {"message": f"Cat with id: {cat_id} and all related photos deleted successfully"}


@router.put("/{cat_id}", response_model=Cat)
async def update_cat_record(cat_id: int, cat_update: CatUpdate, db=Depends(get_db)):
    db_cat = await get_cat(db, cat_id=cat_id)
    if not db_cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    db_cat = await update_cat(db, db_cat, cat_update)
    return db_cat
