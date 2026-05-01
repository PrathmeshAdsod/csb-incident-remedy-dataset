"""IO utilities: HTTP fetching with retry, local caching, file helpers."""

import time
import hashlib
from pathlib import Path
from typing import Optional

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CSBDatasetPipeline/1.0; "
        "+https://github.com/PrathmeshAdsod/csb-incident-remedy-dataset)"
    )
}


def url_to_cache_path(url: str, cache_dir: Path, suffix: str = ".html") -> Path:
    """Convert a URL to a deterministic local cache file path."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return cache_dir / f"{url_hash}{suffix}"


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_url(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
    headers: Optional[dict] = None,
) -> Optional[requests.Response]:
    """
    Fetch a URL with retry logic. Returns Response or None on non-retriable errors.
    """
    _session = session or requests.Session()
    _headers = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        resp = _session.get(url, timeout=timeout, headers=_headers)
        resp.raise_for_status()
        return resp
    except requests.HTTPError as e:
        logger.warning(f"HTTP error {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        raise


def fetch_and_cache(
    url: str,
    cache_dir: Path,
    suffix: str = ".html",
    session: Optional[requests.Session] = None,
    force: bool = False,
) -> Optional[Path]:
    """
    Fetch URL and cache to disk. Returns local path or None on failure.
    If cache exists and force=False, returns cached path without re-fetching.
    """
    cache_path = url_to_cache_path(url, cache_dir, suffix)
    if cache_path.exists() and not force:
        logger.debug(f"Cache hit: {cache_path} for {url}")
        return cache_path

    cache_dir.mkdir(parents=True, exist_ok=True)
    resp = fetch_url(url, session=session)
    if resp is None:
        return None

    cache_path.write_bytes(resp.content)
    logger.debug(f"Cached {url} -> {cache_path}")
    time.sleep(0.5)  # polite crawl delay
    return cache_path


def read_text(path: Path, encoding: str = "utf-8") -> Optional[str]:
    """Read text from a file, returning None on failure."""
    try:
        return path.read_text(encoding=encoding, errors="replace")
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist. Return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path
