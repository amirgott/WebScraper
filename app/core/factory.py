from importlib import import_module
from typing import Type, Dict, Any
from app.core.services import BaseLLMService, BaseScraperService, GoogleSheetsService

class ServiceFactory:
    # Map service types to their base classes and implementation modules
    SERVICE_MAPPINGS = {
        'llm': {
            'base_class': BaseLLMService,
            'implementations': {
                'google_ai': ('app.llm_services.google_ai_llm', 'GoogleAiService'),
                # Add more LLM implementations here
            }
        },
        'scraper': {
            'base_class': BaseScraperService,
            'implementations': {
                'apify': ('app.scraping_services.apify_scraping', 'ApifyScraperService'),
                'scrapy': ('app.scraping_services.scrapy_scraping', 'ScrapyScraperService'),
                # Add more scraper implementations here
            }
        }
    }

    @classmethod
    def create_service(cls, service_type: str, implementation: str, **kwargs) -> Any:
        """
        Dynamically creates a service instance based on type and implementation.

        Args:
            service_type: The type of service (e.g., 'llm', 'scraper')
            implementation: The specific implementation (e.g., 'google_ai', 'apify')
            **kwargs: Configuration parameters for the service
        """
        if service_type not in cls.SERVICE_MAPPINGS:
            raise ValueError(f"Unknown service type: {service_type}")

        service_info = cls.SERVICE_MAPPINGS[service_type]
        implementations = service_info['implementations']

        if implementation not in implementations:
            raise ValueError(
                f"Unknown {service_type} implementation: {implementation}. "
                f"Available options: {list(implementations.keys())}"
            )

        # Get the module path and class name
        module_path, class_name = implementations[implementation]

        try:
            # Dynamically import the module and get the class
            module = import_module(module_path)
            service_class = getattr(module, class_name)

            # Verify that the class inherits from the correct base class
            if not issubclass(service_class, service_info['base_class']):
                raise TypeError(
                    f"{class_name} must inherit from {service_info['base_class'].__name__}"
                )

            # Create and return the service instance
            return service_class(**kwargs)

        except ImportError as e:
            raise ImportError(f"Failed to import {implementation} implementation: {e}")
