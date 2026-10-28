"""
Safe HTTP Regulatory Document Scraper & Adapter
Executes secure HTTP fetches with anti-SSRF checks, streaming size guards,
bounded retries, rate limits, and failure tracking.
"""

import time
import urllib.request
import urllib.error
from typing import List, Optional
from datetime import datetime, timezone

from app.modules.regulatory_intel.adapters.base import (
    BaseSourceAdapter,
    FetchedRegulatoryPayload,
)
from app.modules.regulatory_intel.safeguards import (
    validate_safe_url,
    validate_file_content_safety,
    MAX_DOCUMENT_SIZE_BYTES,
    FileSizeExceededError,
    IngestionSecurityError,
)


class SafeHttpDocumentAdapter(BaseSourceAdapter):
    """
    Production-grade HTTP adapter for official regulator portals (MPCB, CPCB, DISH, Gazette).
    Enforces SSRF prevention, bounded streaming, rate-limiting, and error handling.
    """

    USER_AGENT = "PlantProof-Regulatory-Intelligence/1.0 (+https://plantproof.in/governance; compliance-bot)"

    def __init__(
        self,
        source_code: str,
        base_url: str,
        rate_limit_per_minute: int = 12,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        super().__init__(source_code=source_code, base_url=base_url, rate_limit_per_minute=rate_limit_per_minute)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._last_request_time = 0.0

    def _apply_rate_limit(self) -> None:
        """Enforces minimum interval between consecutive requests to the same portal."""
        min_interval = 60.0 / max(1, self.rate_limit_per_minute)
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def fetch_url_bytes(self, url: str) -> bytes:
        """
        Safely downloads raw bytes from an authorized URL with SSRF checks and streaming size limits.
        """
        safe_url = validate_safe_url(url)
        self._apply_rate_limit()

        req = urllib.request.Request(
            safe_url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/pdf, text/html, application/xhtml+xml, */*",
            }
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    # Check Content-Length header if provided
                    content_len_header = resp.headers.get("Content-Length")
                    if content_len_header:
                        try:
                            content_len = int(content_len_header)
                            if content_len > MAX_DOCUMENT_SIZE_BYTES:
                                raise FileSizeExceededError(content_len, MAX_DOCUMENT_SIZE_BYTES)
                        except ValueError:
                            pass

                    # Stream chunks safely with running size accumulator
                    chunks = []
                    total_bytes = 0
                    chunk_size = 64 * 1024  # 64 KB

                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        if total_bytes > MAX_DOCUMENT_SIZE_BYTES:
                            raise FileSizeExceededError(total_bytes, MAX_DOCUMENT_SIZE_BYTES)
                        chunks.append(chunk)

                    data = b"".join(chunks)
                    mime_type = resp.headers.get_content_type()
                    validate_file_content_safety(data, mime_type)
                    return data

            except urllib.error.HTTPError as e:
                last_error = e
                # Do not retry 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found
                if e.code in (400, 401, 403, 404):
                    raise IngestionSecurityError(f"HTTP {e.code} error fetching regulatory source: {e.reason}")
                # Backoff on 429 or 5xx server errors
                time.sleep(2 ** attempt)

            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_error = e
                time.sleep(2 ** attempt)

        raise ConnectionError(
            f"Failed to fetch regulatory source after {self.max_retries} retries. Last error: {last_error}"
        )

    def poll(self) -> List[FetchedRegulatoryPayload]:
        """
        Generic HTTP poll implementation.
        In production, subclasses or site-specific scrapers parse the circular list HTML/RSS.
        """
        data = self.fetch_url_bytes(self.base_url)
        return [
            FetchedRegulatoryPayload(
                external_id=f"{self.source_code}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
                title=f"Regulatory Publication from {self.source_code}",
                document_url=self.base_url,
                published_date=datetime.now(timezone.utc).date(),
                raw_bytes=data,
                mime_type="application/pdf" if data.startswith(b"%PDF") else "text/html",
            )
        ]
