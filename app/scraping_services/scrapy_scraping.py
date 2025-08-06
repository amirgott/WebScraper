from typing import Dict, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from app.core.services import BaseScraperService


class ScrapyScraperService(BaseScraperService):
    """
    Web scraper service implementation using BeautifulSoup.
    Extracts all text content from a given URL.
    (Still named ScrapyScraperService for compatibility)
    """
    def __init__(self, *args, **kwargs):
        print("Web scraper initialized.")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_url(self, url: str) -> str:
        """
        Scrapes the given URL and extracts all text content.

        Args:
            url (str): URL to scrape

        Returns:
            str: All text content extracted from the URL
        """
        print(f"Scraping URL: {url}...")

        try:
            # Fetch the webpage
            response = self.session.get(url, timeout=30)
            response.raise_for_status()  # Raise an exception for bad status codes

            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
                element.decompose()

            # Extract all text
            text_content = soup.get_text(separator=' ', strip=True)

            # Normalize whitespace
            text_content = ' '.join(text_content.split())

            if not text_content:
                return "No content was extracted from the URL."

            # Format result as required by the scraper interface
            result = text_content

            print(f"Successfully extracted {len(text_content)} characters from {url}")
            return result

        except requests.RequestException as e:
            error_message = f"Error while scraping URL {url}: {str(e)}"
            print(error_message)
            return error_message
        except Exception as e:
            error_message = f"Unexpected error while scraping URL {url}: {str(e)}"
            print(error_message)
            return error_message
