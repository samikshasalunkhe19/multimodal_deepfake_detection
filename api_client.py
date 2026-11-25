"""Thin wrapper around the backend API so the UI code stays simple."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api").rstrip("/")
ANALYZE_TIMEOUT = 900      # long videos can take a few minutes on CPU


class ApiError(Exception):
    """Raised with a message that is safe to show to the user."""


def _handle(resp: requests.Response) -> Any:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        if isinstance(detail, list):                       # FastAPI 422 format
            detail = "; ".join(str(d.get("msg", d)) for d in detail)
        raise ApiError(str(detail)[:500])
    return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.content


def _request(method: str, path: str, timeout: int = 30, **kwargs) -> Any:
    try:
        return _handle(requests.request(method, f"{API_URL}{path}", timeout=timeout, **kwargs))
    except requests.ConnectionError:
        raise ApiError(f"Cannot reach the backend at {API_URL}. Start it with: uvicorn backend.main:app --port 8000")
    except requests.Timeout:
        raise ApiError("The backend took too long to answer.")


def health() -> Dict[str, Any]:
    return _request("GET", "/health", timeout=4)


def analyze_file(kind: str, filename: str, data: bytes, mime: Optional[str] = None) -> Dict[str, Any]:
    files = {"file": (filename, data, mime or "application/octet-stream")}
    return _request("POST", f"/analyze/{kind}", timeout=ANALYZE_TIMEOUT, files=files)


def analyze_multimodal(files: Dict[str, tuple]) -> Dict[str, Any]:
    """files: kind -> (filename, bytes, mime)"""
    return _request("POST", "/analyze/multimodal", timeout=ANALYZE_TIMEOUT, files=files)


def list_history(limit: int = 50, offset: int = 0, file_type: Optional[str] = None) -> Dict[str, Any]:
    params = {"limit": limit, "offset": offset}
    if file_type:
        params["file_type"] = file_type
    return _request("GET", "/history", params=params)


def delete_history(analysis_id: str) -> None:
    _request("DELETE", f"/history/{analysis_id}")


def report_pdf(analysis_id: str) -> bytes:
    return _request("GET", f"/history/{analysis_id}/report.pdf", timeout=60)
