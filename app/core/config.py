import os
from dotenv import load_dotenv


class Config:
    """
    Configuration class to load environment variables.
    """
    def __init__(self):
        load_dotenv()
        self.APIFY_API_KEY: str = os.getenv("APIFY_API_KEY")
        self.GOOGLE_AI_STUDIO_KEY: str = os.getenv("GOOGLE_AI_STUDIO_KEY")
        self.GOOGLE_SERVICE_ACCOUNT_PATH: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
        self.GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID")
        self.FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5000")

        # Service type configurations
        self.LLM_SERVICE_TYPE: str = os.getenv("LLM_SERVICE_TYPE", "google_ai")
        self.SCRAPER_SERVICE_TYPE: str = os.getenv("SCRAPER_SERVICE_TYPE", "apify")

config = Config()