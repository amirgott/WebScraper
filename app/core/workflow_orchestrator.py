import re
import base64
import json
from io import BytesIO
from typing import List, Optional
try:
    from PIL import Image
except ImportError:
    Image = None
    print("Warning: PIL not available, image processing will be disabled")

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    print("Warning: PyPDF2 not available, PDF processing will be disabled")

from urllib.parse import urljoin, urlparse

from app.api.models import EventRecord, WorkflowResult
from app.core.services import BaseLLMService, BaseScraperService
from app.core.url_utils import extract_urls_from_text, is_valid_url, normalize_url

class WorkflowOrchestrator:
    def __init__(self, llm_service: BaseLLMService, scraper_service: BaseScraperService, ocr_service=None, schema_file: str = "event_details_schema.json"):
        self.llm_service = llm_service
        self.scraper_service = scraper_service
        self.ocr_service = ocr_service
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
                print(f"Warning: Failed to read schema file {self.schema_file}: {e}")
                # Fallback to basic schema
                self._schema_content = {
                    "תאריך": {"description": "Event date", "format": "DD.MM.YY"},
                    "שם_האירוع": {"description": "Event name", "format": "text"},
                    "תוכן": {"description": "Event description", "format": "text"}
                }
        return self._schema_content

    def _dict_to_event_record(self, data_dict: dict) -> EventRecord:
        """Convert dictionary to EventRecord, handling missing or extra fields"""
        try:
            # Filter out any keys that aren't EventRecord fields
            event_fields = EventRecord.__fields__.keys()
            filtered_data = {k: v for k, v in data_dict.items() if k in event_fields}
            return EventRecord(**filtered_data)
        except Exception as e:
            print(f"Error converting dict to EventRecord: {e}")
            # Return a basic EventRecord with error information
            basic_record = EventRecord()
            basic_record.Error = f"Data conversion error: {str(e)}"
            return basic_record

    async def process_text_workflow(self, text: str, event_record: EventRecord, depth: int = 0) -> WorkflowResult:
        """
        Process text input to extract event information and discover URLs.
        """
        try:
            # Extract event information from text using LLM
            # Note: process_data expects a schema, using empty dict as placeholder
            extracted_data = self.llm_service.process_data(text, {})

            # Merge with existing event record
            self._merge_event_data(event_record, extracted_data)

            # Discover URLs in the text
            discovered_urls = []
            if depth == 0:  # Only discover URLs at depth 0
                discovered_urls = extract_urls_from_text(text)
                discovered_urls = [normalize_url(url) for url in discovered_urls if is_valid_url(url)]

            return WorkflowResult(
                source_type="text",
                source_content=text[:500] + "..." if len(text) > 500 else text,
                extracted_data=extracted_data,
                discovered_urls=discovered_urls
            )

        except Exception as e:
            return WorkflowResult(
                source_type="text",
                source_content=text[:500] + "..." if len(text) > 500 else text,
                extracted_data=EventRecord(),
                errors=[str(e)]
            )

    async def process_url_workflow(self, url: str, event_record: EventRecord, depth: int = 0) -> WorkflowResult:
        """
        Process URL by scraping and applying text workflow.
        """
        try:
            # Scrape the URL
            scraped_content = await self.scraper_service.scrape_url(url)

            # Process the scraped text
            text_result = await self.process_text_workflow(scraped_content, event_record, depth)

            # Look for images in the scraped content if at depth 0
            image_urls = []
            if depth == 0:
                image_urls = self._extract_image_urls(scraped_content, url)

                # Process found images
                for img_url in image_urls[:3]:  # Limit to first 3 images
                    try:
                        img_result = await self.process_image_workflow(img_url, event_record)
                        # Add image URL to event record if it contains relevant info
                        if img_result.extracted_data and any(getattr(img_result.extracted_data, field) for field in ['תאריך', 'שם_האירוע', 'משעה']):
                            if not event_record.IMAGE:
                                event_record.IMAGE = img_url
                    except Exception as e:
                        print(f"Error processing image {img_url}: {e}")

            return WorkflowResult(
                source_type="url",
                source_content=url,
                extracted_data=text_result.extracted_data,
                discovered_urls=text_result.discovered_urls if depth == 0 else None
            )

        except Exception as e:
            return WorkflowResult(
                source_type="url",
                source_content=url,
                extracted_data=EventRecord(),
                errors=[str(e)]
            )

    async def process_image_workflow(self, image_input, event_record: EventRecord) -> WorkflowResult:
        """
        Process image using OCR and LLM to extract event information.
        """
        try:
            # Handle different image input types
            if isinstance(image_input, str):
                if image_input.startswith('data:image'):
                    # Base64 encoded image from frontend
                    image_data = base64.b64decode(image_input.split(',')[1])
                    image = Image.open(BytesIO(image_data))
                elif image_input.startswith('http'):
                    # Image URL - download and process
                    image = await self._download_image(image_input)
                else:
                    raise ValueError("Invalid image input format")
            else:
                # File upload or other binary data
                image = Image.open(BytesIO(image_input))

            # Perform OCR
            if self.ocr_service:
                ocr_text = self.ocr_service.extract_text(image)
            else:
                ocr_text = ""
                print("Warning: OCR service not available, skipping text extraction from image")

            if not ocr_text.strip():
                return WorkflowResult(
                    source_type="image",
                    source_content="No text found in image or OCR not available",
                    extracted_data=EventRecord()
                )

            # Process OCR text with LLM
            extracted_data_dict = self.llm_service.process_data(ocr_text, self.schema_content)
            extracted_data = self._dict_to_event_record(extracted_data_dict)

            # Merge with existing event record
            self._merge_event_data(event_record, extracted_data)

            # Save image URL if this image contains relevant event info
            if isinstance(image_input, str) and image_input.startswith('http'):
                if any(getattr(extracted_data, field) for field in ['תאריך', 'שם_האירוע', 'משעה']):
                    if not event_record.IMAGE:
                        event_record.IMAGE = image_input

            return WorkflowResult(
                source_type="image",
                source_content=f"OCR Text: {ocr_text[:200]}..." if len(ocr_text) > 200 else f"OCR Text: {ocr_text}",
                extracted_data=extracted_data
            )

        except Exception as e:
            return WorkflowResult(
                source_type="image",
                source_content="Error processing image",
                extracted_data=EventRecord(),
                errors=[str(e)]
            )

    async def process_pdf_workflow(self, pdf_content: bytes, event_record: EventRecord) -> WorkflowResult:
        """
        Process PDF by extracting text and applying text workflow.
        """
        try:
            # Extract text from PDF
            pdf_text = self._extract_pdf_text(pdf_content)

            if not pdf_text.strip():
                return WorkflowResult(
                    source_type="pdf",
                    source_content="No text found in PDF",
                    extracted_data=EventRecord()
                )

            # Process PDF text with text workflow
            result = await self.process_text_workflow(pdf_text, event_record, depth=0)
            result.source_type = "pdf"

            return result

        except Exception as e:
            return WorkflowResult(
                source_type="pdf",
                source_content="Error processing PDF",
                extracted_data=EventRecord(),
                errors=[str(e)]
            )

    def _merge_event_data(self, target: EventRecord, source: EventRecord):
        """
        Merge event data from source into target, handling conflicts.
        """
        errors = []

        for field_name, field_value in source.dict().items():
            if field_value is not None and field_value != "":
                existing_value = getattr(target, field_name)

                if existing_value is None or existing_value == "":
                    setattr(target, field_name, field_value)
                elif existing_value != field_value:
                    # Conflict detected
                    errors.append(f"Conflict in {field_name}: '{existing_value}' vs '{field_value}'")

        if errors:
            current_errors = target.Error if target.Error else ""
            target.Error = current_errors + "; " + "; ".join(errors) if current_errors else "; ".join(errors)

    def _extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF using PyPDF2."""
        try:
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""

            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""

    def _extract_image_urls(self, html_content: str, base_url: str) -> List[str]:
        """Extract image URLs from HTML content."""
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(img_pattern, html_content, re.IGNORECASE)

        image_urls = []
        for match in matches:
            if match.startswith('http'):
                image_urls.append(match)
            else:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, match)
                image_urls.append(absolute_url)

        return image_urls

    async def _download_image(self, image_url: str) -> Image.Image:
        """Download image from URL."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return Image.open(BytesIO(image_data))
                else:
                    raise Exception(f"Failed to download image: {response.status}")
