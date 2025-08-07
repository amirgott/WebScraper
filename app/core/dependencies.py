from app.core.config import config
from app.core.services import BaseLLMService, BaseScraperService, GoogleSheetsService, ScrapingService
from app.core.factory import ServiceFactory

# Service instances - initialized on first access
_llm_service_instance = None
_scraper_service_instance = None
_google_sheets_service_instance = None
_scraping_service_instance = None

def get_llm_service() -> BaseLLMService:
    """
    Returns a singleton instance of the configured LLM service.
    The actual implementation is determined by the LLM_SERVICE_TYPE config.
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = ServiceFactory.create_service(
            service_type='llm',
            implementation=config.LLM_SERVICE_TYPE,
            api_key=config.GOOGLE_AI_STUDIO_KEY
        )
    return _llm_service_instance

def get_scraper_service() -> BaseScraperService:
    """
    Returns a singleton instance of the configured scraper service.
    The actual implementation is determined by the SCRAPER_SERVICE_TYPE config.
    Supports 'apify' and 'scrapy' implementations.
    """
    global _scraper_service_instance
    if _scraper_service_instance is None:
        kwargs = {}
        # Add implementation-specific parameters
        if config.SCRAPER_SERVICE_TYPE == 'apify':
            kwargs['api_key'] = config.APIFY_API_KEY
        # For 'scrapy' implementation, no special parameters are needed
        # but we ensure it's properly handled

        _scraper_service_instance = ServiceFactory.create_service(
            service_type='scraper',
            implementation=config.SCRAPER_SERVICE_TYPE,
            **kwargs
        )
    return _scraper_service_instance

def get_google_sheets_service():
    """
    Returns a singleton instance of the GoogleSheetsService.
    """
    global _google_sheets_service_instance
    if _google_sheets_service_instance is None:
        _google_sheets_service_instance = GoogleSheetsService(
            service_account_path=config.GOOGLE_SERVICE_ACCOUNT_PATH,
            output_sheet_id=config.GOOGLE_SHEET_ID,
            input_sheet_id=config.GOOGLE_INPUT_SHEET_ID if hasattr(config, 'GOOGLE_INPUT_SHEET_ID') else None
        )
    return _google_sheets_service_instance

def get_scraping_service() -> ScrapingService:
    """
    Returns a singleton instance of the ScrapingService.
    """
    global _scraping_service_instance
    if _scraping_service_instance is None:
        _scraping_service_instance = ScrapingService(
            scraper=get_scraper_service(),
            llm=get_llm_service()
        )
    return _scraping_service_instance