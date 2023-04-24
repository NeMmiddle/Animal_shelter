from fastapi import FastAPI

from cats import models
from cats.router import router as cats_operation
from database import engine, create_database

# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Animal Shelter")


@app.on_event("startup")
async def startup():
    await create_database()


app.include_router(cats_operation)
