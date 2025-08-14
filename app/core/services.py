from abc import ABC, abstractmethod
import json
import gspread
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List


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

class ScrapingService:
    """
    Service to handle the scraping and processing workflow.
    """
    def __init__(
        self,
        scraper: BaseScraperService,
        llm: BaseLLMService,
        schema_file: str = "event_details_schema.json"
    ):
        self.scraper = scraper
        self.llm = llm
        self.schema_file = schema_file
        self._schema_content = None

    @property
    def schema_content(self):
        """Lazy loading of schema content"""
        if self._schema_content is None:
            try:
                with open(self.schema_file, 'r', encoding='utf-8') as file:
                    self._schema_content = json.load(file)
            except Exception as e:
                raise RuntimeError(f"Failed to read schema file: {e}")
        return self._schema_content

    def process_url(self, url: str) -> Dict[str, Any]:
        """
        Scrapes and processes a single URL.
        Returns the processed data.
        """
        try:
            raw_content = self.scraper.scrape_url(url)
            llm_response = self.llm.process_data(raw_content, self.schema_content)
            return llm_response
        except Exception as e:
            raise RuntimeError(f"Error processing URL {url}: {str(e)}")

class GoogleSheetsService:
    """
    Service to interact with Google Sheets for input and output operations.
    """

    def __init__(self, service_account_path: str, output_sheet_id: str, input_sheet_id: str = None):
        if not service_account_path or not output_sheet_id:
            raise ValueError("Google Sheets credentials or sheet ID are not provided.")

        try:
            self.gc = gspread.service_account(filename=service_account_path)
            self.output_sheet = self.gc.open_by_key(output_sheet_id).sheet1
            self.input_sheet = None
            if input_sheet_id:
                self.input_sheet = self.gc.open_by_key(input_sheet_id).sheet1
            print("Successfully connected to Google Sheets.")
        except Exception as e:
            raise RuntimeError(f"Could not connect to Google Sheets. Check your credentials and sheet IDs. Error: {e}")

    def get_next_url(self) -> Tuple[Optional[str], Optional[int]]:
        """
        Gets the next URL from the input sheet.
        Returns a tuple of (url, row_number) or (None, None) if no URLs are available.
        """
        if not self.input_sheet:
            raise ValueError("Input sheet is not configured.")

        try:
            # Assuming URLs are in column A, starting from row 2 (row 1 is headers)
            values = self.input_sheet.col_values(1)
            if len(values) <= 1:  # Only header or empty
                return None, None

            # Get first non-empty URL after header
            for idx, value in enumerate(values[1:], start=2):  # Start from row 2
                if value.strip():
                    return value.strip(), idx

            return None, None
        except Exception as e:
            print(f"Error reading from input sheet: {e}")
            return None, None

    def get_all_urls(self) -> List[Dict[str, Any]]:
        """
        Gets all URLs from the input sheet.
        Returns a list of dictionaries with 'url' and 'row' keys.
        """
        if not self.input_sheet:
            raise ValueError("Input sheet is not configured.")

        try:
            urls = []
            values = self.input_sheet.col_values(1)

            # Skip header row
            for idx, value in enumerate(values[1:], start=2):
                if value.strip():
                    urls.append({"url": value.strip(), "row": idx})

            return urls
        except Exception as e:
            print(f"Error reading all URLs from input sheet: {e}")
            return []

    def delete_url(self, row_number: int) -> bool:
        """
        Deletes a URL from the input sheet by row number.
        Returns True if successful, False otherwise.
        """
        if not self.input_sheet:
            raise ValueError("Input sheet is not configured.")

        try:
            self.input_sheet.delete_rows(row_number)
            return True
        except Exception as e:
            print(f"Error deleting row {row_number}: {e}")
            return False

    def write_data(self, url, data: Dict[str, Any]) -> bool:
        """
        Adds a new row to the output Google Sheet.
        Returns True if successful, False otherwise.
        """
        try:
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

            # Get the next available row and insert data there
            next_row = len(self.output_sheet.get_all_values()) + 1
            self.output_sheet.insert_row(list_data, next_row)
            print(f"Data successfully written to row {next_row}.")
            return True
        except Exception as e:
            print(f"Error writing to output sheet: {e}")
            return False

    def write_event_record(self, event_record) -> bool:
            """
            Write an EventRecord to the output sheet with proper Hebrew column mapping.
            """
            try:
                from app.api.models import EventRecord

                # Define the column mapping based on the Hebrew schema
                column_mapping = {
                    'תאריך': 'A',
                    'משעה': 'B', 
                    'עד_שעה': 'C',
                    'שם_האירוע': 'D',
                    'תעשיה': 'E',
                    'תעשיה_2': 'F',
                    'אירועי_פיזי_אונליין': 'G',
                    'תוכן': 'H',
                    'חברה_מארחת': 'I',
                    'חברות_נוספות': 'J',
                    'מרצה_מארח': 'K',
                    'מרצים_נוספים': 'L',
                    'לינק_להרשמה': 'M',
                    'לינקים_נוספים': 'N',
                    'IMAGE': 'O',
                    'עלות': 'P',
                    'אי_מייל_למשתתפים': 'Q',
                    'יום_בשבוע': 'R',
                    'IN_CALENDAR': 'S',
                    'Error': 'T'
                }

                # Get the next empty row
                next_row = len(self.output_sheet.get_all_values()) + 1

                # Prepare the row data
                row_data = []
                event_dict = event_record.dict() if hasattr(event_record, 'dict') else event_record

                for field_name in column_mapping.keys():
                    value = event_dict.get(field_name, '')

                    # Handle list fields
                    if isinstance(value, list):
                        value = ', '.join(str(v) for v in value if v)

                    # Handle None values
                    if value is None:
                        value = ''

                    row_data.append(str(value))

                # Write the row
                range_name = f"A{next_row}:T{next_row}"
                self.output_sheet.update(range_name, [row_data])

                print(f"Successfully wrote event record to row {next_row}")
                return True

            except Exception as e:
                print(f"Error writing event record: {str(e)}")
                return False