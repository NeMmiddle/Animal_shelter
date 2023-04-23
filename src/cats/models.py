from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Cat(Base):
    __tablename__ = "cats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    species = Column(String)
    breed = Column(String)
    age = Column(Integer)

    photos = relationship("Photo", back_populates="cat")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String)
    cat_id = Column(Integer, ForeignKey("cats.id"))

    cat = relationship("Cat", back_populates="photos")
