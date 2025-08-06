from abc import ABC, abstractmethod

import gspread
from datetime import datetime
from typing import Dict, Any


class BaseLLMService(ABC):
    """
    Abstract base class for LLM services.
    """

    @abstractmethod
    def __init__(self, api_key: str):
        """Initialize the LLM service with the required API key."""
        pass

    @abstractmethod
    def process_data(self, data: str, schema_content) -> Dict[str, Any]:
        """
        Process the input data using the LLM service.
        Args:
            data: Input text to process
            schema_content: Schema defining the expected output format

        Returns:
            Dict[str, Any]: Processed data in the format specified by the schema
        """
        pass

# --- Abstract Base Scraper Class ---
class BaseScraperService(ABC):
    """
    Abstract base class for all scraper services.
    Defines the common interface for different scraper implementations.
    """
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def scrape_url(self, url: str) -> str:
        """
        Abstract method to scrape a given URL and return structured data.
        Implementations must return a dictionary containing at least
        'eventTime' (or similar specific data) and 'fullPageText'.
        """
        pass

class GoogleSheetsService:
    """
    Service to write data to Google Sheets using gspread.
    """

    def __init__(self, service_account_path: str, sheet_id: str):
        if not service_account_path or not sheet_id:
            raise ValueError("Google Sheets credentials are not provided.")

        try:
            self.gc = gspread.service_account(filename=service_account_path)
            self.sheet = self.gc.open_by_key(sheet_id).sheet1
            print("Successfully connected to Google Sheet.")
        except Exception as e:
            raise RuntimeError(f"Could not connect to Google Sheets. Check your credentials and sheet ID. Error: {e}")

    def write_data(self, url, data: Dict[str, Any]):
        """
        Appends a new row to the Google Sheet.
        """
        print("Writing data to Google Sheet...")
        list_data = [
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # חותמת זמן
                       url
                   ] + [
                       ", ".join(value) if isinstance(value, list) else value if value else ""
                       # Process list or empty values
                       for field in data.keys()
                       for value in [data.get(field, None)]
                       # Ensure schema_fields keys are handled when missing in result
                   ] + [
                       "Success",
                       ""
                   ]

        self.sheet.append_row(list_data)
        print("Data successfully written.")