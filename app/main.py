"""FastAPI entry point. Run from the project root:  uvicorn app.main:app --reload"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()  # loads .env before anything reads GOOGLE_API_KEY

from app.database import init_db  # noqa: E402
from app.routes import router  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="FitBuddy - AI Fitness Plan Generator", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.include_router(router)
