import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any

from app.core.dependencies import get_llm_service, get_scraper_service, get_google_sheets_service
from app.core.services import BaseLLMService, BaseScraperService, GoogleSheetsService

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

@router.post("/scrape")
async def scrape_and_process(
        payload: URLPayload,
        scraper: BaseScraperService = Depends(get_scraper_service),
        llm: BaseLLMService = Depends(get_llm_service)
):
    """
    Scrapes a URL and processes the content with an LLM.
    Returns the processed data to the user for review.
    """
    try:
        raw_content = scraper.scrape_url(payload.url)
        schema_file = "event_details_schema.json"
        try:
            with open(schema_file, 'r', encoding='utf-8') as file:
                schema_content = json.load(file)
        except Exception as e:
            raise RuntimeError(f"Failed to read schema file: {e}")

        llm_response = llm.process_data(raw_content, schema_content)
        processed_data = {'result': llm_response}
        persistent_data[payload.url] = llm_response
        return JSONResponse(content=processed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_data(url: str, gsheets=Depends(get_google_sheets_service)):
    """
    Confirm and write the processed data to Google Sheets. Data is retrieved
    by the URL from `persistent_data`.
    """
    try:
        # Check if the URL exists in the persistent_data dictionary
        if url not in persistent_data:
            raise HTTPException(status_code=404, detail="No data found for the given URL.")

        gsheets.write_data(url, persistent_data[url])

        return JSONResponse(
            content={"message": "Data written to Google Sheets successfully."},
            status_code=200
        )
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