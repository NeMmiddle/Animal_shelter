from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form, Body

from cats.schemas import Cat, CatCreate, CatWithPhotos, PhotoCreate, CatUpdate
from cats.service import (create_cat, create_cat_photos, get_cat,
                          get_cat_with_photos, get_cats, delete_cat, update_cat, create_cat_with_photos)
from database import get_db

router = APIRouter(prefix="/cats", tags=["Cats"])


@router.get("/all", response_model=list[Cat])
async def get_all_cats(skip: int = 0, limit: int = 20, db=Depends(get_db)):
    cats = await get_cats(db, skip=skip, limit=limit)
    return cats


@router.get("/{cat_id}", response_model=CatWithPhotos)
async def get_only_cat(cat_id: int, db=Depends(get_db)):
    cat = await get_cat_with_photos(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    return cat


@router.post("/cat", response_model=CatWithPhotos)
async def create_complete_cat_model(
        name: str = Form(default='Сat destroyer'),
        age: int = Form(default=3),
        gender: str = Form(default='male'),
        about: str = Form(default='about'),
        sterilized: bool = Form(default=True),
        files: List[UploadFile] = File(...),
        db=Depends(get_db)
):
    cat = CatCreate(
        name=name,
        age=age,
        gender=gender,
        about=about,
        sterilized=sterilized
    )
    cat = await create_cat_with_photos(db, cat, files)
    returning_cat = await get_cat_with_photos(db, cat_id=cat.id)
    return returning_cat


@router.post("/only_cat", response_model=Cat)
async def create_cat_without_pictures(cat: CatCreate, db=Depends(get_db)):
    return await create_cat(db, cat)


@router.post("/{cat_id}/only_photos")
async def upload_cat_photos(cat_id: int, files: List[UploadFile] = File(...), db=Depends(get_db)):
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    for file in files:
        photo = PhotoCreate(url=file.filename, cat_id=cat_id)
        await create_cat_photos(db, photo, file, cat)
    return {"detail": "Photos uploaded successfully"}


@router.put("/{cat_id}", response_model=Cat)
async def update_cat_by_id(cat_id: int, cat_update: CatUpdate, db=Depends(get_db)):
    db_cat = await get_cat(db, cat_id=cat_id)
    if not db_cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    db_cat = await update_cat(db, db_cat, cat_update)
    return db_cat


@router.delete("/{cat_id}")
async def delete_cat_by_id(cat_id: int, db=Depends(get_db)):
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    await delete_cat(db, cat)
    return {"message": f"Cat with id:{cat_id} and all related photos deleted successfully"}
