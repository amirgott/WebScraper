import re
from urllib.parse import urlparse, urljoin, urlunparse
from typing import List

def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract URLs from text using regex patterns.
    """
    # Regex pattern to match URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

    urls = re.findall(url_pattern, text)
    return urls

def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid and accessible.
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)
    except:
        return False

def normalize_url(url: str) -> str:
    """
    Normalize URL by ensuring proper scheme and cleaning up.
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed = urlparse(url)
    # Remove fragment and clean up
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path,
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))

    return normalized

def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except:
        return ""

def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs belong to the same domain.
    """
    return extract_domain(url1) == extract_domain(url2)

def is_url_only_text(text: str) -> str:
    """
    Check if text contains only a single URL (with optional whitespace).
    Returns the URL if it's URL-only text, otherwise returns None.
    """
    if not text or not text.strip():
        return None

    # Remove leading/trailing whitespace
    cleaned_text = text.strip()

    # Check if the entire text is a single URL
    if is_valid_url(cleaned_text):
        # Double-check that there's no additional text
        # by ensuring the URL takes up most/all of the cleaned text
        extracted_urls = extract_urls_from_text(cleaned_text)
        if len(extracted_urls) == 1 and extracted_urls[0] == cleaned_text:
            return normalize_url(cleaned_text)

    return None
