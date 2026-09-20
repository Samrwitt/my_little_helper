from app.services.scraping.scraper import FetchResult, ScholarshipScraper
from app.services.scraping.ssrf import UnsafeURLError, normalize_url, validate_public_url

__all__ = [
    "FetchResult",
    "ScholarshipScraper",
    "UnsafeURLError",
    "normalize_url",
    "validate_public_url",
]
