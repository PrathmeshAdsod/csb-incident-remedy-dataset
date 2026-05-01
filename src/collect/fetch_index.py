"""
Stage 1a: Discover and index CSB incident, recommendation, and report pages.

CSB public base URLs used:
  - https://www.csb.gov/investigations/
  - https://www.csb.gov/recommendations/

Outputs sources_manifest.csv.
"""

import csv
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.utils.io_utils import fetch_url, ensure_dir
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

CSB_BASE = "https://www.csb.gov"
INVESTIGATIONS_URL = "https://www.csb.gov/investigations/"
RECOMMENDATIONS_URL = "https://www.csb.gov/recommendations/"

MANIFEST_COLUMNS = [
    "url",
    "source_type",
    "title",
    "incident_id",
    "date_discovered",
    "raw_cache_path",
    "notes",
]


def discover_investigation_pages(
    session: requests.Session,
    limit: Optional[int] = None,
) -> list[dict]:
    """
    Crawl the CSB investigations listing page(s) and return
    a list of dicts with url, title, source_type.
    """
    records = []
    page = 1
    seen_urls: set[str] = set()

    while True:
        # CSB uses ?page=N or similar pagination
        paginated_url = f"{INVESTIGATIONS_URL}?page={page}"
        logger.info(f"Fetching investigation index page {page}: {paginated_url}")
        resp = fetch_url(paginated_url, session=session)
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "lxml")

        # CSB investigation listing: links to /investigations/<slug>/
        links = soup.select("a[href*='/investigations/']") or soup.find_all("a", href=True)
        found_new = False
        for a in links:
            href = a.get("href", "")
            if "/investigations/" not in href:
                continue
            full_url = urljoin(CSB_BASE, href).rstrip("/") + "/"
            if full_url in seen_urls or full_url == INVESTIGATIONS_URL:
                continue
            # Exclude generic list pages
            if full_url.rstrip("/") == INVESTIGATIONS_URL.rstrip("/"):
                continue
            seen_urls.add(full_url)
            title = a.get_text(strip=True) or ""
            records.append(
                {
                    "url": full_url,
                    "source_type": "incident_page",
                    "title": title,
                    "incident_id": _extract_incident_id_from_url(full_url),
                    "date_discovered": _today(),
                    "raw_cache_path": "",
                    "notes": "",
                }
            )
            found_new = True
            if limit and len(records) >= limit:
                break

        if not found_new:
            logger.info("No new links found, stopping pagination.")
            break

        # Check for a next-page link
        next_link = soup.select_one("a[rel='next'], a.next, li.next a")
        if not next_link:
            break

        page += 1
        time.sleep(1)

        if limit and len(records) >= limit:
            break

    return records


def discover_recommendation_pages(
    session: requests.Session,
    limit: Optional[int] = None,
) -> list[dict]:
    """
    Crawl the CSB recommendations listing page(s) and return records.
    """
    records = []
    page = 1
    seen_urls: set[str] = set()

    while True:
        paginated_url = f"{RECOMMENDATIONS_URL}?page={page}"
        logger.info(f"Fetching recommendation index page {page}: {paginated_url}")
        resp = fetch_url(paginated_url, session=session)
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.select("a[href*='/recommendations/']") or soup.find_all("a", href=True)
        found_new = False
        for a in links:
            href = a.get("href", "")
            if "/recommendations/" not in href:
                continue
            full_url = urljoin(CSB_BASE, href).rstrip("/") + "/"
            if full_url in seen_urls or full_url.rstrip("/") == RECOMMENDATIONS_URL.rstrip("/"):
                continue
            seen_urls.add(full_url)
            title = a.get_text(strip=True) or ""
            records.append(
                {
                    "url": full_url,
                    "source_type": "recommendation_page",
                    "title": title,
                    "incident_id": _extract_incident_id_from_url(full_url),
                    "date_discovered": _today(),
                    "raw_cache_path": "",
                    "notes": "",
                }
            )
            found_new = True
            if limit and len(records) >= limit:
                break

        if not found_new:
            break

        next_link = soup.select_one("a[rel='next'], a.next, li.next a")
        if not next_link:
            break

        page += 1
        time.sleep(1)

        if limit and len(records) >= limit:
            break

    return records


def _extract_incident_id_from_url(url: str) -> str:
    """
    Attempt to extract an incident ID from the URL slug.
    e.g. /investigations/2010-08-i-wa-tesoro-anacortes-refinery/ -> 2010-08-i-wa
    """
    parts = [p for p in url.rstrip("/").split("/") if p]
    if parts:
        slug = parts[-1]
        # Match pattern like YYYY-MM-I-XX
        import re
        match = re.match(r"(\d{4}-\d{2}-i-[a-z]{2})", slug, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return slug[:40]  # fallback: truncated slug
    return ""


def _today() -> str:
    import datetime
    return datetime.date.today().isoformat()


def save_manifest(records: list[dict], output_path: Path) -> None:
    """Write the manifest CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for rec in records:
            # Fill missing keys with empty string
            row = {col: rec.get(col, "") for col in MANIFEST_COLUMNS}
            writer.writerow(row)
    logger.info(f"Saved manifest with {len(records)} records -> {output_path}")


def run_discover(
    output_dir: Path,
    limit: Optional[int] = None,
    verbose: bool = False,
) -> Path:
    """Entry point for the discover stage."""
    global logger
    logger = get_logger(__name__, log_file=output_dir / "logs" / "discover.log", verbose=verbose)
    ensure_dir(output_dir / "raw")

    session = requests.Session()
    records = []

    investigation_records = discover_investigation_pages(session, limit=limit)
    logger.info(f"Discovered {len(investigation_records)} investigation pages.")
    records.extend(investigation_records)

    if not limit or len(records) < limit:
        remaining = None if not limit else limit - len(records)
        rec_records = discover_recommendation_pages(session, limit=remaining)
        logger.info(f"Discovered {len(rec_records)} recommendation pages.")
        records.extend(rec_records)

    manifest_path = output_dir / "sources_manifest.csv"
    save_manifest(records, manifest_path)
    return manifest_path
