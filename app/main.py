import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from dotenv import load_dotenv

from app.api.endpoints import router as api_router
from app.core.config import config

# Load environment variables from .env file
load_dotenv()

def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    """
    app = FastAPI(title="URL Processing API")

    # Configure CORS middleware
    # In a production environment, you should restrict origins to your frontend URL
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount the static directory to serve the frontend
    # This will serve the index.html file at the root URL '/'
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Include the API router
    app.include_router(api_router)

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)