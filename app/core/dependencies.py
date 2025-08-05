from app.core.config import config
from app.core.services import LLMService, ApifyScraperService, ScrapyScraperService, GoogleSheetsService, BaseScraperService

# Dependency to get a singleton LLMService instance.
llm_service_instance = LLMService(api_key=config.GOOGLE_AI_STUDIO_KEY)

def get_llm_service():
    return llm_service_instance

# Dependency to get a singleton ScraperService instance.
scraper_service_instance = ScraperService(api_key=config.APIFY_API_KEY)

# Dependency to get the appropriate ScraperService instance based on config.
# This function will return an instance that adheres to BaseScraperService interface.
def get_scraper_service() -> BaseScraperService:
    if config.SCRAPER_TYPE == "apify":
        # Ensure ApifyScraperService is initialized only once
        if not hasattr(get_scraper_service, '_apify_instance'):
            get_scraper_service._apify_instance = ApifyScraperService(api_key=config.APIFY_API_KEY)
        return get_scraper_service._apify_instance
    elif config.SCRAPER_TYPE == "scrapy":
        # Ensure ScrapyScraperService is initialized only once
        if not hasattr(get_scraper_service, '_scrapy_instance'):
            get_scraper_service._scrapy_instance = ScrapyScraperService()
        return get_scraper_service._scrapy_instance
    else:
        raise ValueError(f"Unknown SCRAPER_TYPE: {config.SCRAPER_TYPE}. Must be 'apify' or 'scrapy'.")

# Dependency to get a singleton GoogleSheetsService instance.
google_sheets_service_instance = GoogleSheetsService(
    service_account_path=config.GOOGLE_SERVICE_ACCOUNT_PATH,
    sheet_id=config.GOOGLE_SHEET_ID
)

def get_google_sheets_service():
    return google_sheets_service_instance