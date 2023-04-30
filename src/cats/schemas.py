from datetime import datetime
from typing import List

from pydantic import BaseModel


class CatBase(BaseModel):
    name: str
    age: int
    gender: str
    about: str
    sterilized: bool


class CatCreate(CatBase):
    pass


class CatUpdate(CatBase):
    pass

    class Config:
        orm_mode = True


class Cat(CatBase):
    id: int
    views: int
    registered_at: datetime

    class Config:
        orm_mode = True


class PhotoBase(BaseModel):
    url: str
    cat_id: int


class PhotoCreate(PhotoBase):
    pass


class Photo(PhotoBase):
    pass

    class Config:
        orm_mode = True


class CatWithPhotos(Cat):
    photos: List[Photo] = []

    class Config:
        orm_mode = True
