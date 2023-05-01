from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from cats.schemas import CatCreate, CatUpdate, CatWithPhotos
from cats.service import (
    add_photos_for_the_cat,
    create_cat_with_photos,
    delete_cat,
    delete_photo,
    get_cat,
    get_cat_and_photo,
    get_cats,
    update_cat,
)
from database import get_db

router = APIRouter(prefix="/cats", tags=["Cats"])


@router.get("/all", response_model=List[CatWithPhotos])
async def get_all_cats(skip: int = 0, limit: int = 20, db=Depends(get_db)):
    """
    Get all cats.
    """
    return await get_cats(db, skip=skip, limit=limit)


@router.get("/{cat_id}", response_model=CatWithPhotos)
async def get_cat_on_id(cat_id: int, db=Depends(get_db)):
    """
    Get one cat by id.
    """
    return await get_cat(db, cat_id=cat_id)


@router.post("/cat")
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
    (Photos do not need to be added immediately,
    this can be done later using the 'upload_cat_photos' router)
    And also inside the create_cat_with_photos method we save photos to google drive
    using the upload_photos_to_google_drive method.
    """

    cat = CatCreate(
        name=name, age=age, gender=gender, about=about, sterilized=sterilized
    )
    await create_cat_with_photos(db, cat, files)
    return {"message": "Upload was successful!"}


@router.post("/{cat_id}/only_photos")
async def upload_cat_photos_to_drive(
    cat_id: int, files: List[UploadFile] = File(None), db=Depends(get_db)
):
    """
    Add photos to a cat by its id and upload them to Google Drive.
    """
    await add_photos_for_the_cat(db, files, cat_id)
    return {"detail": "Photos uploaded successfully"}


@router.patch("/{cat_id}", response_model=CatWithPhotos)
async def update_cat_by_id(cat_id: int, cat_update: CatUpdate, db=Depends(get_db)):
    """
    We can update the fields of an existing cat and the name of its photos folder in Google Drive.
    """
    db_cat = await update_cat(db, cat_id, cat_update)
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

    await delete_cat(db, cat.id)
    return {
        "message": f"Cat with id:{cat_id} and all related photos deleted successfully"
    }


@router.delete("/cats/{cat_id}/photos/{photo_id}")
async def delete_cat_photo_handler(cat_id: int, photo_id: int, db=Depends(get_db)):
    """
    Delete a photo of a cat by ID.
    """
    cat, photo = await get_cat_and_photo(db, cat_id=cat_id, photo_id=photo_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Cat not found")
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.cat_id != cat.id:
        raise HTTPException(status_code=400, detail="Photo does not belong to the cat")

    await delete_photo(db=db, photo_id=photo_id)
    return {"message": "Photo deleted successfully"}
