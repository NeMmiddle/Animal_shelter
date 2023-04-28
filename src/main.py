from fastapi import FastAPI

from cats.router import router as cats_operation
from database import create_database

app = FastAPI(title="Animal Shelter")


@app.on_event("startup")
async def startup():
    await create_database()


app.include_router(cats_operation)
