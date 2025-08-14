import json
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image

from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from app.core.dependencies import (
    get_llm_service, get_scraper_service, get_google_sheets_service, 
    get_scraping_service, get_workflow_orchestrator, get_ocr_service
)
from app.core.services import BaseLLMService, BaseScraperService, GoogleSheetsService, ScrapingService
from app.api.models import EventRecord, WorkflowResult
from app.core.url_utils import is_url_only_text

router = APIRouter()


class URLPayload(BaseModel):
    url: str


from pydantic import BaseModel, HttpUrl, EmailStr
from typing import List, Optional

# Persistent data dictionary
persistent_data = {}

class ProcessedDataPayload(BaseModel):
    תאריך: Optional[str]  # Expected format: "DD.MM.YY"
    משעה: Optional[str]  # Expected format: "HH:MM"
    עד_שעה: Optional[str]  # Expected format: "HH:MM"
    שם_האירוע: Optional[str]  # Event name
    תעשיה: Optional[str]  # Industry (e.g., "ESG וקיימות")
    תעשיה_2: Optional[str] = None  # Always empty
    אירועי_פיזי_אונליין: Optional[str]  # Physical/Online event type
    תוכן: Optional[str]  # Event description or details
    חברה_מארחת: Optional[str]  # Hosting company or organization
    חברות_נוספות: Optional[List[str]]  # Up to 3 companies
    מרצה_מארח: Optional[str]  # Hosting speaker or organizer
    מרצים_נוספים: Optional[List[str]]  # Up to 4 additional speakers
    לינק_להרשמה: Optional[HttpUrl]  # Registration link (URL)
    לינקים_נוספים: Optional[List[HttpUrl]]  # Additional URLs
    IMAGE: Optional[HttpUrl]  # Event image URL
    עלות: Optional[str]  # Cost (or "ללא עלות" for no cost)
    אי_מייל_למשתתפים: Optional[EmailStr]  # Participants contact email
    יום_בשבוע: Optional[str]  # Day of the week (derived from date)
    IN_CALENDAR: Optional[bool] = None  # Always empty by requirement

@router.get("/input-urls")
async def get_input_urls(
    gsheets: GoogleSheetsService = Depends(get_google_sheets_service)
):
    """
    Retrieves all URLs from the input sheet.
    """
    try:
        if not gsheets.input_sheet:
            raise HTTPException(status_code=400, detail="Input sheet not configured")

        urls = []

        # Get all values from the first column (A)
        values = gsheets.input_sheet.col_values(1)

        # Skip header row (row 1)
        for idx, value in enumerate(values[1:], start=2):
            if value.strip():
                urls.append({"url": value.strip(), "row": idx})

        return JSONResponse(content={"urls": urls})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape")
async def scrape_and_process(
        payload: URLPayload,
        scraping_service: ScrapingService = Depends(get_scraping_service)
):
    """
    Scrapes a URL and processes the content with an LLM.
    Returns the processed data to the user for review.
    """
    try:
        llm_response = scraping_service.process_url(payload.url)
        processed_data = {'result': llm_response}
        persistent_data[payload.url] = llm_response
        return JSONResponse(content=processed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ConfirmPayload(BaseModel):
    url: str
    row_number: Optional[int] = None

@router.post("/confirm")
async def confirm_data(
    payload: ConfirmPayload,
    gsheets=Depends(get_google_sheets_service)
):
    """
    Confirm and write the processed data to Google Sheets. Data is retrieved
    by the URL from `persistent_data`. If row_number is provided, also delete
    the URL from the input sheet.
    """
    try:
        # Check if the URL exists in the persistent_data dictionary
        if payload.url not in persistent_data:
            raise HTTPException(status_code=404, detail="No data found for the given URL.")

        # Write to output sheet
        if not gsheets.write_data(payload.url, persistent_data[payload.url]):
            raise HTTPException(status_code=500, detail="Failed to write data to output sheet")

        # If row number is provided, delete from input sheet
        if payload.row_number and gsheets.input_sheet:
            if gsheets.delete_url(payload.row_number):
                return JSONResponse(
                    content={
                        "message": "Data written to output sheet and URL removed from input sheet.",
                        "url": payload.url
                    },
                    status_code=200
                )
            else:
                return JSONResponse(
                    content={
                        "message": "Data written to output sheet but failed to delete URL from input sheet.",
                        "url": payload.url
                    },
                    status_code=207  # Partial success
                )

        return JSONResponse(
            content={"message": "Data written to Google Sheets successfully."},
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-sheet")
async def process_sheet(
    scraping_service: ScrapingService = Depends(get_scraping_service),
    gsheets: GoogleSheetsService = Depends(get_google_sheets_service)
):
    """
    Processes one URL from the input sheet, writes results to output sheet,
    and deletes the processed URL from input sheet.
    """
    try:
        # Get next URL to process
        url, row_number = gsheets.get_next_url()
        if not url:
            return JSONResponse(
                content={"message": "No URLs available for processing."},
                status_code=200
            )

        # Use the common scraping service
        llm_response = scraping_service.process_url(url)

        # Write to output sheet
        if gsheets.write_data(url, llm_response):
            # If write was successful, delete from input sheet
            if gsheets.delete_url(row_number):
                return JSONResponse(
                    content={
                        "message": "URL processed successfully and removed from input sheet.",
                        "url": url,
                        "processed_data": llm_response
                    },
                    status_code=200
                )
            else:
                return JSONResponse(
                    content={
                        "message": "Data processed and written, but failed to delete URL from input sheet.",
                        "url": url,
                        "processed_data": llm_response
                    },
                    status_code=207  # Partial success
                )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to write processed data to output sheet"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def webhook_trigger(request: Request):
    """
    Webhook endpoint that receives triggers and processes URLs.
    """
    try:
        # Get the raw data from the webhook
        data = await request.json()
        print(f"Received webhook trigger: {data}")

        # Extract URL from the webhook data
        url = None
        if isinstance(data, dict):
            # Try common field names for URL
            url = (data.get('url') or 
                   data.get('link') or 
                   data.get('webpage') or 
                   data.get('site') or
                   data.get('page_url'))

        if not url:
            print(f"Could not extract URL from webhook data: {data}")
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "No URL found in webhook data",
                    "received_data": data
                },
                status_code=400
            )

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        print(f"Processing URL from webhook: {url}")

        # For now, just return success without processing
        # TODO: Add actual processing once Google Sheets is configured
        return JSONResponse(
            content={
                "status": "success",
                "message": "Webhook received successfully",
                "url": url,
                "note": "Processing disabled until Google Sheets is configured"
            },
            status_code=200
        )

    except json.JSONDecodeError:
        return JSONResponse(
            content={"status": "error", "message": "Invalid JSON format"},
            status_code=400
        )
    except Exception as e:
        print(f"Webhook processing error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.post("/run_scrape")
async def run_scrape_endpoint(
    text_input: Optional[str] = Form(None),
    image_data: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    workflow_orchestrator = Depends(get_workflow_orchestrator)
):
    """
    Main endpoint that handles all three input types and orchestrates workflows.
    """
    try:
        # Initialize event record
        event_record = EventRecord()
        all_discovered_urls = []
        workflow_results = []

        # Process text input
        if text_input and text_input.strip():
            # Check if text contains only a URL
            url_only = is_url_only_text(text_input)
            if url_only:
                # Use URL workflow for URL-only text
                result = await workflow_orchestrator.process_url_workflow(url_only, event_record, depth=0)
                workflow_results.append(result)
                if result.discovered_urls:
                    all_discovered_urls.extend(result.discovered_urls)
            else:
                # Use text workflow for regular text content
                result = await workflow_orchestrator.process_text_workflow(text_input.strip(), event_record, depth=0)
                workflow_results.append(result)
                if result.discovered_urls:
                    all_discovered_urls.extend(result.discovered_urls)

        # Process image input
        if image_data:
            result = await workflow_orchestrator.process_image_workflow(image_data, event_record)
            workflow_results.append(result)

        # Process PDF input
        if pdf_file:
            pdf_content = await pdf_file.read()
            result = await workflow_orchestrator.process_pdf_workflow(pdf_content, event_record)
            workflow_results.append(result)

        # Process discovered URLs (depth 1 only)
        for url in all_discovered_urls:
            try:
                result = await workflow_orchestrator.process_url_workflow(url, event_record, depth=1)
                workflow_results.append(result)
            except Exception as e:
                print(f"Error processing discovered URL {url}: {e}")

        # Store results for potential confirmation
        request_id = f"{datetime.now().timestamp()}"
        persistent_data[request_id] = {
            'event_record': event_record,
            'workflow_results': workflow_results
        }

        return JSONResponse(content={
            'request_id': request_id,
            'event_record': event_record.dict(),
            'workflow_results': [result.dict() for result in workflow_results],
            'summary': {
                'total_workflows': len(workflow_results),
                'discovered_urls_count': len(all_discovered_urls)
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/write_to_sheet")
async def write_to_sheet(
    request_data: dict,
    gsheets: GoogleSheetsService = Depends(get_google_sheets_service)
):
    """
    Write the processed event record to Google Sheets.
    """
    try:
        request_id = request_data.get('request_id')

        if not request_id or request_id not in persistent_data:
            raise HTTPException(status_code=404, detail="Request ID not found")

        event_record = persistent_data[request_id]['event_record']

        # Write to Google Sheets
        success = gsheets.write_event_record(event_record)

        if success:
            # Clean up persistent data
            del persistent_data[request_id]
            return JSONResponse(content={"message": "Successfully written to Google Sheets"})
        else:
            raise HTTPException(status_code=500, detail="Failed to write to Google Sheets")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improve")
async def improve_data(
        payload: ProcessedDataPayload,
        llm: BaseLLMService = Depends(get_llm_service)
):
    """
    Triggers a re-processing of the data (currently a placeholder).
    """
    try:
        # Placeholder for future implementation
        # For example, send the current data back to the LLM with new instructions.
        print("Improve endpoint called with data:", payload.dict())

        # Simulate an improved response
        improved_data = payload.dict()
        improved_data["summary"] = f"Improved summary based on user feedback: {payload.summary}"

        return JSONResponse(content=improved_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))