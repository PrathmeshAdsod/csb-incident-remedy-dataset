"""
Stage 1b: Fetch and cache all HTML pages listed in sources_manifest.csv.
Updates raw_cache_path column after successful fetch.
"""

import csv
import time
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm

from src.utils.io_utils import fetch_and_cache, url_to_cache_path, ensure_dir
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def fetch_all_pages(
    manifest_path: Path,
    raw_dir: Path,
    limit: Optional[int] = None,
    force: bool = False,
    verbose: bool = False,
) -> Path:
    """
    Read sources_manifest.csv, fetch each URL, cache HTML,
    update raw_cache_path in the manifest.
    Returns updated manifest path.
    """
    global logger
    logger = get_logger(
        __name__,
        log_file=manifest_path.parent / "logs" / "fetch_pages.log",
        verbose=verbose,
    )
    ensure_dir(raw_dir)
    session = requests.Session()

    rows = []
    with open(manifest_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            rows.append(row)

    updated_rows = []
    for row in tqdm(rows, desc="Fetching pages", disable=not verbose):
        url = row.get("url", "")
        if not url:
            row["notes"] = "missing url"
            updated_rows.append(row)
            continue

        cache_path = fetch_and_cache(
            url=url,
            cache_dir=raw_dir,
            suffix=".html",
            session=session,
            force=force,
        )
        if cache_path:
            row["raw_cache_path"] = str(cache_path)
        else:
            row["notes"] = f"{row.get('notes', '')} | fetch_failed".strip(" |")
        updated_rows.append(row)
        time.sleep(0.3)

    # Write back
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    logger.info(f"Fetched {len(updated_rows)} pages. Manifest updated: {manifest_path}")
    return manifest_path
