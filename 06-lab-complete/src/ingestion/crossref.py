import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
import requests

from core.config import Settings
from core.utils import ensure_parent, write_json, read_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def clean_xml_tags(text: str) -> str:
    """Helper to remove XML/HTML tags and clean whitespace."""
    if not text:
        return ""
    # Remove HTML/XML tags
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_date(item: dict) -> str:
    """Helper to extract publication date as YYYY-MM-DD from Crossref metadata."""
    for key in ["published-print", "published-online", "issued", "created"]:
        date_parts = item.get(key, {}).get("date-parts")
        if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
            parts = date_parts[0]
            try:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
                return f"{year:04d}-{month:02d}-{day:02d}"
            except (ValueError, TypeError):
                continue
    return "2026-01-01"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload to list of PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records = []
    for item in items:
        paper_id = item.get("DOI", "")
        if not paper_id:
            continue

        # Title
        titles = item.get("title", [])
        if isinstance(titles, list):
            title = titles[0] if titles else "Unknown Title"
        else:
            title = str(titles)

        # Abstract/Summary
        abstract = clean_xml_tags(item.get("abstract", ""))

        # Authors
        authors_list = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = author.get("name", "").strip()
            if given or family:
                full_name = f"{given} {family}".strip()
            elif name:
                full_name = name
            else:
                continue
            authors_list.append(full_name)

        # Categories
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else "General"

        # Dates
        published = extract_date(item)
        updated = extract_date(item)  # Fallback to published date

        # URLs
        abs_url = item.get("URL", "")
        pdf_url = ""
        for link in item.get("link", []):
            if "pdf" in link.get("content-type", "").lower():
                pdf_url = link.get("URL", "")
                break
        if not pdf_url:
            pdf_url = abs_url

        comment = ""

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=abstract,
                authors=authors_list,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Call source API, save raw response, parse to records."""
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "RAG-Observability-Agent/1.0 (mailto:agentic-rag-lab@example.com)"
    }

    max_retries = 3
    retry_delay = 2
    response_payload = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                response_payload = response.json()
                break
            elif response.status_code in (429, 503):
                time.sleep(retry_delay * (attempt + 1))
            else:
                response.raise_for_status()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to fetch Crossref data: {e}")
            time.sleep(retry_delay * (attempt + 1))

    if not response_payload:
        raise RuntimeError("Failed to fetch Crossref data after retries.")

    # Save raw response
    write_json(settings.paths.raw_api_response, response_payload)

    # Parse payload
    records = parse_crossref_payload(response_payload)

    # Save raw records as dict list
    records_dict = [asdict(record) for record in records]
    write_json(settings.paths.raw_records_json, records_dict)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and map to PaperRecord."""
    data = read_json(path)
    records = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item["primary_category"],
                published=item["published"],
                updated=item["updated"],
                abs_url=item["abs_url"],
                pdf_url=item["pdf_url"],
                comment=item.get("comment", ""),
            )
        )
    return records

