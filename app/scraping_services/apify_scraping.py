from apify_client import ApifyClient
from app.core.services import BaseScraperService

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


