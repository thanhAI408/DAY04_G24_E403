from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "fbclid", "gclid"}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def normalize_url(value: Any, remove_tracking_params: bool = True) -> str:
    raw = _text(value)
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parts.path.rstrip("/") or "/"
        query = parts.query
        if remove_tracking_params:
            query = urlencode([(k, v) for k, v in parse_qsl(query, keep_blank_values=True)
                               if k.lower() not in TRACKING_PARAMS])
        return urlunsplit((scheme, netloc, path, query, ""))
    except ValueError:
        return raw.lower().rstrip("/")


def normalize_title(value: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", _text(value).lower(), flags=re.UNICODE)).strip()


def deduplicate_research_items(
    items: list[dict[str, Any]] | None = None,
    similarity_threshold: float = 0.85,
    remove_tracking_params: bool = True,
) -> dict[str, Any]:
    if not isinstance(items, list):
        return {"error": "invalid_input", "message": "items must be a list"}
    try:
        threshold = max(0.0, min(1.0, float(similarity_threshold)))
    except (TypeError, ValueError):
        return {"error": "invalid_input", "message": "similarity_threshold must be numeric"}

    unique: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        if not isinstance(raw, dict):
            return {"error": "invalid_input", "message": f"items[{index}] must be an object"}
        item = dict(raw)
        url_key = normalize_url(item.get("url"), remove_tracking_params)
        title_key = normalize_title(item.get("title"))
        match_index = None
        for candidate_index, candidate in enumerate(unique):
            candidate_url = normalize_url(candidate.get("url"), remove_tracking_params)
            candidate_title = normalize_title(candidate.get("title"))
            same_url = bool(url_key and candidate_url and url_key == candidate_url)
            similar_title = bool(title_key and candidate_title and SequenceMatcher(None, title_key, candidate_title).ratio() >= threshold)
            if same_url or (not url_key and not candidate_url and similar_title) or (url_key and candidate_url and similar_title):
                match_index = candidate_index
                break
        if match_index is None:
            unique.append(item)
        else:
            group = next((g for g in groups if g["canonical_index"] == match_index), None)
            if group is None:
                group = {"canonical_index": match_index, "item_indices": [match_index], "items": [unique[match_index]]}
                groups.append(group)
            group["item_indices"].append(index)
            group["items"].append(item)
    return {
        "unique_items": unique,
        "duplicate_groups": groups,
        "original_count": len(items),
        "unique_count": len(unique),
        "removed_count": len(items) - len(unique),
    }
