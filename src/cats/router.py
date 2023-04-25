from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from cats.schemas import Cat, CatCreate, CatUpdate, CatWithPhotos, PhotoCreate
from cats.service import (create_cat_photos,
                          create_cat_with_photos, delete_cat, get_cat,
                          get_cat_with_photos, get_cats, update_cat)
from database import get_db

router = APIRouter(prefix="/cats", tags=["Cats"])


@router.get("/all", response_model=list[Cat])
async def get_all_cats(skip: int = 0, limit: int = 20, db=Depends(get_db)):
    """
    Get all cats.
    """
    cats = await get_cats(db, skip=skip, limit=limit)
    return cats


@router.get("/{cat_id}", response_model=CatWithPhotos)
async def get_only_cat(cat_id: int, db=Depends(get_db)):
    """
    Get one cat by id.
    """
    cat = await get_cat_with_photos(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    return cat


@router.post("/cat", response_model=CatWithPhotos)
async def create_complete_cat_model(
        name: str = Form(default="Сat destroyer"),
        age: int = Form(default=3),
        gender: str = Form(default="male"),
        about: str = Form(default="about"),
        sterilized: bool = Form(default=True),
        files: List[UploadFile] = File(None),
        db=Depends(get_db),
):
    """
    Send a form to fill in the model of the cat and its photos.
    (Photos do not need to be added immediately, this can be done later using the 'upload_cat_photos' router)
    And also inside the create_cat_with_photos method we save photos locally
    using the save_photo_to_directory internal method.
    """

    cat = CatCreate(
        name=name, age=age, gender=gender, about=about, sterilized=sterilized
    )
    cat = await create_cat_with_photos(db, cat, files)
    returning_cat = await get_cat_with_photos(db, cat_id=cat.id)
    return returning_cat


@router.post("/{cat_id}/only_photos")
async def upload_cat_photos(
        cat_id: int, files: List[UploadFile] = File(...), db=Depends(get_db)
):
    """
    Add photos to a cat by its id.
    """
    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    for file in files:
        photo = PhotoCreate(url=file.filename, cat_id=cat_id)
        await create_cat_photos(db, photo, file, cat)
    return {"detail": "Photos uploaded successfully"}


@router.put("/{cat_id}", response_model=Cat)
async def update_cat_by_id(cat_id: int, cat_update: CatUpdate, db=Depends(get_db)):
    """
    We can change the fields of an existing cat.
    """
    db_cat = await get_cat(db, cat_id=cat_id)
    if not db_cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    db_cat = await update_cat(db, db_cat, cat_update)
    return db_cat


@router.delete("/{cat_id}")
async def delete_cat_by_id(cat_id: int, db=Depends(get_db)):
    """
    We delete a cat by id and all photos associated
    with it both locally and in the database.
    """

    cat = await get_cat(db, cat_id=cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    await delete_cat(db, cat)
    return {
        "message": f"Cat with id:{cat_id} and all related photos deleted successfully"
    }
