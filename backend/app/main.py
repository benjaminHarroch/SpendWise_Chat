from fastapi import FastAPI
from app.api.health_router import router as health_router

app = FastAPI()

app.include_router(health_router)