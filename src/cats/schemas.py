from datetime import datetime
from typing import List, Dict, Union

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


class PhotoBase(BaseModel):
    url: str
    cat_id: int


class PhotoCreate(PhotoBase):
    pass


class Photo(PhotoBase):
    id: int

    class Config:
        orm_mode = True


class Cat(CatBase):
    registered_at: datetime
    views: int
    id: int

    class Config:
        orm_mode = True


class CatWithPhotos(Cat):
    photos: List[Photo] = []

    class Config:
        orm_mode = True
