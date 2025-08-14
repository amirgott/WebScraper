from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Any
from fastapi import UploadFile, File, Form

class RunScrapeRequest(BaseModel):
    text_input: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded image
    pdf_file: Optional[UploadFile] = None

class EventRecord(BaseModel):
    תאריך: Optional[str] = None
    משעה: Optional[str] = None
    עד_שעה: Optional[str] = None
    שם_האירוע: Optional[str] = None
    תעשיה: Optional[str] = None
    תעשיה_2: Optional[str] = None
    אירועי_פיזי_אונליין: Optional[str] = None
    תוכן: Optional[str] = None
    חברה_מארחת: Optional[str] = None
    חברות_נוספות: Optional[List[str]] = None
    מרצה_מארח: Optional[str] = None
    מרצים_נוספים: Optional[List[str]] = None
    לינק_להרשמה: Optional[str] = None  # Changed from HttpUrl to str to avoid validation issues
    לינקים_נוספים: Optional[List[str]] = None  # Changed from List[HttpUrl] to List[str]
    IMAGE: Optional[str] = None  # Changed from HttpUrl to str
    עלות: Optional[str] = None
    אי_מייל_למשתתפים: Optional[str] = None
    יום_בשבוע: Optional[str] = None
    IN_CALENDAR: Optional[bool] = None
    Error: Optional[str] = None

    class Config:
        # Allow arbitrary field names (for Hebrew characters)
        allow_population_by_field_name = True

class WorkflowResult(BaseModel):
    source_type: str  # 'text', 'url', 'image', 'pdf'
    source_content: str
    extracted_data: EventRecord
    discovered_urls: Optional[List[str]] = None
    errors: Optional[List[str]] = None

    class Config:
        # Allow arbitrary field names
        allow_population_by_field_name = True
