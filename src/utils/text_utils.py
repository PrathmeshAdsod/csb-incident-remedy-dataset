"""Text utility functions for cleaning, truncating, and extracting spans."""

import re
import hashlib
from typing import Optional


def clean_whitespace(text: str) -> str:
    """Normalize whitespace in a string."""
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate text to max_chars, appending ellipsis if truncated."""
    text = clean_whitespace(text)
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "..."
    return text


def extract_span(
    full_text: str,
    keyword: str,
    context_chars: int = 300,
    case_sensitive: bool = False,
) -> Optional[str]:
    """
    Extract a context window around the first occurrence of keyword in full_text.
    Returns None if keyword not found.
    """
    if not keyword or not full_text:
        return None
    flags = 0 if case_sensitive else re.IGNORECASE
    match = re.search(re.escape(keyword), full_text, flags=flags)
    if not match:
        return None
    start = max(0, match.start() - context_chars // 2)
    end = min(len(full_text), match.end() + context_chars // 2)
    span = full_text[start:end]
    return clean_whitespace(span)


def extract_sentences_containing(
    full_text: str, keyword: str, max_sentences: int = 3
) -> Optional[str]:
    """
    Return up to max_sentences sentences containing keyword.
    Sentences are split on period/exclamation/question.
    """
    if not keyword or not full_text:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", full_text)
    matched = [
        s.strip()
        for s in sentences
        if keyword.lower() in s.lower()
    ]
    if not matched:
        return None
    return " ".join(matched[:max_sentences])


def stable_hash(text: str, length: int = 8) -> str:
    """Return a short stable hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Try to parse and normalize date strings to ISO 8601 (YYYY-MM-DD).
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    import datetime

    date_str = clean_whitespace(date_str)
    formats = [
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%B %Y",
        "%b %Y",
        "%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            if fmt in ("%B %Y", "%b %Y"):
                return dt.strftime("%Y-%m-01")
            if fmt == "%Y":
                return dt.strftime("%Y-01-01")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def remove_html_tags(text: str) -> str:
    """Strip HTML tags from a string."""
    return re.sub(r"<[^>]+>", " ", text)


def is_mostly_empty(text: Optional[str], min_chars: int = 20) -> bool:
    """Return True if text is None or shorter than min_chars after stripping."""
    if not text:
        return True
    return len(text.strip()) < min_chars
