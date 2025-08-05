from abc import ABC, abstractmethod

import gspread
import json
from datetime import datetime
import google.generativeai as genai
from apify_client import ApifyClient
from typing import Dict, Any


class LLMService:
    """
    Service to interact with the LLM (Google Gemini).
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google AI Studio key is not provided.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        print("LLMService initialized with gemini-2.5-pro model.")

    def process_data(self, data: str, schema_content) -> Dict[str, Any]:
        """
        Uses the Gemini LLM to format the scraped data.
        Returns a dictionary with predefined properties.
        """
        print("Processing data with Google Gemini LLM...")

        formatted_schema = ', '.join(
            [f"[{field}: {details['description']} ({details['format']})]" for field, details in schema_content.items()])

        # Craft a prompt to instruct the LLM to return a JSON object
        prompt = f"""
        Analyze the below text content from a web page. 
        Extract and summarize the content into a JSON object with the following properties:
        {formatted_schema}.

        The final output must be a single JSON object. Do not include any other text or formatting.
        It is important to assign the HttpUrl fields with the URL values from the text. 
        
        Text Content:
        {data[:3000]} 
        """

        try:
            # Make the API call to the Gemini model
            response = self.model.generate_content(prompt)
            # The model's response contains the JSON as a string
            json_str = response.text.strip().replace("`", "").replace("json", "").strip()

            # Parse the JSON string into a Python dictionary
            processed_data = json.loads(json_str)

            # Add the raw content length, which is better calculated locally
            # processed_data["raw_content_length"] = len(data)

            return processed_data
        except Exception as e:
            print(f"Error processing with LLM: {e}")
            raise RuntimeError(f"LLM processing failed. Please check the API key and model output.")


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
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Abstract method to scrape a given URL and return structured data.
        Implementations must return a dictionary containing at least
        'eventTime' (or similar specific data) and 'fullPageText'.
        """
        pass

# --- Scrapy Scraper Implementation (Placeholder) ---
class ScrapyScraperService(BaseScraperService): # Inherit from BaseScraperService
    """
    Placeholder service for a Scrapy-based scraper.
    NOTE: Integrating a full Scrapy project into a FastAPI application
    is complex and typically involves running Scrapy spiders as separate
    processes or using a dedicated Scrapy API. This implementation
    is a basic placeholder to demonstrate the interface.
    """
    def __init__(self, *args, **kwargs):
        print("ScrapyScraperService initialized (placeholder).")
        # In a real scenario, you might initialize Scrapy settings or
        # a client to communicate with a ScrapyD server here.
        pass

    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Placeholder implementation for Scrapy scraping.
        """
        print(f"Scraping URL: {url} with Scrapy (placeholder)...")
        # A real Scrapy integration would involve:
        # 1. Defining a Scrapy spider to extract the desired data.
        # 2. Running the spider (e.g., using CrawlerProcess or a subprocess call).
        # 3. Capturing the output (e.g., to a JSON file or by sending items to a pipeline).
        # 4. Parsing the Scrapy output into the required dictionary format.

        # Simulate Scrapy output for demonstration
        return {
            "eventTime": "Scrapy Placeholder Time: 10:00 01.01.2026",
            "fullPageText": f"This is placeholder content scraped by Scrapy from {url}. A real Scrapy spider would extract actual data."
        }
class ApifyScraperService(BaseScraperService): # Inherit from BaseScraperService
    """
    Service to scrape URLs using Apify.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Apify API key is not provided.")
        self.client = ApifyClient(api_key)

    def scrape_url(self, url: str) -> str:
        """
        Runs the Apify 'Website Content Crawler' actor and returns the text content.
        """
        print(f"Scraping URL: {url} with Apify...")

        # Define the actor and input
        # Enhanced run_input with more arguments for comprehensive scraping
        run_input = {
            "startUrls": [{"url": url}],
            "crawlerType": "playwright:firefox", # Use a full browser for JavaScript rendering
            "useSitemaps": True,               # Discover more pages via sitemaps
            "maxCrawlPages": 50,               # Limit the total number of pages to crawl
            "maxCrawlDepth": 2,                # Limit the recursive crawling depth (0 = only start URLs)
            "waitFor": "networkidle",          # Wait for network activity to settle before scraping
            "maxScrollHeight": 5000,           # Scroll down to capture content from infinite scrolling pages (e.g., 5000px)
            "removeCookieWarnings": True,      # Attempt to remove cookie banners
            "htmlProcessing": {
                "ignoreHtmlElements": [        # List elements to ignore (keep empty to capture everything)
                    # "header", "footer", "nav", "aside", ".sidebar", ".ad-container"
                ]
            }
        }
        actor_run = self.client.actor("apify/website-content-crawler").call(run_input=run_input)

        # Get the dataset items from the actor run
        dataset_items = self.client.dataset(actor_run["defaultDatasetId"]).list_items().items

        if not dataset_items:
            return "No content found."

        # Extract the text content from the first item
        content = dataset_items[0].get("text", "")
        return content


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