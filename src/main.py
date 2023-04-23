from fastapi import FastAPI

from cats import models
from cats.router import router as cats_operation
from database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Animal Shelter")

app.include_router(cats_operation)
