"""
Stage 1c: Discover and fetch CSB report PDFs linked from incident pages.
Stores PDFs in raw_dir/pdfs/. Adds PDF records to manifest.
"""

import csv
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from src.utils.io_utils import fetch_and_cache, read_text, url_to_cache_path, ensure_dir
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

CSB_BASE = "https://www.csb.gov"


def extract_pdf_links(html: str, base_url: str) -> list[str]:
    """Extract all PDF href links from an HTML page."""
    soup = BeautifulSoup(html, "lxml")
    pdf_urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            full = urljoin(base_url, href)
            pdf_urls.append(full)
    return list(set(pdf_urls))


def discover_and_fetch_pdfs(
    manifest_path: Path,
    raw_dir: Path,
    limit: Optional[int] = None,
    force: bool = False,
    verbose: bool = False,
) -> Path:
    """
    For each cached incident HTML page in the manifest, find PDF links,
    download them, and append new rows to the manifest.
    Returns updated manifest path.
    """
    global logger
    logger = get_logger(
        __name__,
        log_file=manifest_path.parent / "logs" / "fetch_pdfs.log",
        verbose=verbose,
    )
    pdf_dir = ensure_dir(raw_dir / "pdfs")
    session = requests.Session()

    existing_rows = []
    with open(manifest_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            existing_rows.append(row)

    existing_pdf_urls = {
        r["url"] for r in existing_rows if r.get("source_type") == "pdf_report"
    }

    new_pdf_rows = []
    processed = 0
    for row in tqdm(existing_rows, desc="Scanning for PDFs", disable=not verbose):
        cache_path_str = row.get("raw_cache_path", "")
        if not cache_path_str or not Path(cache_path_str).exists():
            continue
        if row.get("source_type") not in ("incident_page", "recommendation_page"):
            continue

        html = read_text(Path(cache_path_str))
        if not html:
            continue

        pdf_urls = extract_pdf_links(html, row["url"])
        for pdf_url in pdf_urls:
            if pdf_url in existing_pdf_urls:
                continue
            existing_pdf_urls.add(pdf_url)

            cache_path = fetch_and_cache(
                url=pdf_url,
                cache_dir=pdf_dir,
                suffix=".pdf",
                session=session,
                force=force,
            )
            new_pdf_rows.append(
                {
                    "url": pdf_url,
                    "source_type": "pdf_report",
                    "title": f"PDF from {row['title']}",
                    "incident_id": row.get("incident_id", ""),
                    "date_discovered": row.get("date_discovered", ""),
                    "raw_cache_path": str(cache_path) if cache_path else "",
                    "notes": f"linked_from: {row['url']}",
                }
            )

        processed += 1
        if limit and processed >= limit:
            break

    all_rows = existing_rows + new_pdf_rows
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info(f"Discovered {len(new_pdf_rows)} PDFs. Manifest updated: {manifest_path}")
    return manifest_path
