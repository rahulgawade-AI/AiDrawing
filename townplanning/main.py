from fastapi import FastAPI

from townplanning.core.settings import get_settings
from townplanning.core.logging import configure_logging


settings = get_settings()

logger = configure_logging(
    settings.LOG_LEVEL
)

app = FastAPI(

    title=settings.APP_NAME,

    version=settings.APP_VERSION,

)


@app.get("/")
async def root():

    return {

        "application": settings.APP_NAME,

        "version": settings.APP_VERSION,

        "status": "healthy",

    }


@app.get("/health")
async def health():

    return {

        "status": "healthy"

    }
