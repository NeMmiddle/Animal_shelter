from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Cat(Base):
    __tablename__ = "cats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=False)
    about = Column(String, nullable=True)
    sterilized = Column(Boolean, nullable=False)
    registered_at = Column(TIMESTAMP, default=datetime.utcnow)
    views = Column(Integer, default=0)
    google_folder_id = Column(String, nullable=True)

    photos = relationship("Photo", back_populates="cat")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String)
    cat_id = Column(Integer, ForeignKey("cats.id"))

    cat = relationship("Cat", back_populates="photos")
