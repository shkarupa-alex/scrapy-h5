"""Scrapy Downloader Middleware for html5-based HTML parsing."""

from scrapy import Request, Spider, signals
from scrapy.crawler import Crawler
from scrapy.http import HtmlResponse, Response

from scrapy_h5.response import HtmlFiveResponse

_HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}


class HtmlFiveResponseMiddleware:
    """Downloader Middleware that replaces HtmlResponse with HtmlFiveResponse.

    This middleware intercepts HTML responses and replaces them with
    HtmlFiveResponse instances, which use html5 for parsing instead of lxml.

    Settings:
        HTML5_BACKEND: str | None (default: 'lexbor')
            Global enable/disable for html5 parsing.

    Per-request control:
        Set request.meta['use_html5'] = False to disable for a specific request.
        Set request.meta['use_html5'] = 'html5ever' to force enable (overrides HTML5_BACKEND=False).

    Usage in settings.py:
        DOWNLOADER_MIDDLEWARES = {
            'scrapy_h5.HtmlFiveResponseMiddleware': 543,
        }
        HTML5_BACKEND = 'html5ever'  # optional, 'lexbor' by default
    """

    def __init__(self, *, backend: str | None = "lexbor") -> None:
        if backend not in {"lexbor", "html5ever", None}:
            raise ValueError(f"Unsupported html5 backend: {backend}")
        self.backend = backend

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "HtmlFiveResponseMiddleware":
        """Create middleware instance from crawler settings."""
        backend = crawler.settings.get("HTML5_BACKEND", default="lexbor")
        middleware = cls(backend=backend)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider: Spider) -> None:
        """Log when spider opens."""
        spider.logger.debug(
            "HtmlFiveResponseMiddleware backend=%s (html5 parsing for HTML responses)",
            self.backend,
        )

    def process_response(
        self,
        request: Request,
        response: Response,
    ) -> Response:
        """Process response and optionally replace with HtmlFiveResponse.

        Handles two cases:
        1. Response is already HtmlResponse - replace with HtmlFiveResponse
        2. Response is plain Response but has HTML content-type - convert to HtmlResponse then HtmlFiveResponse
        """
        # Check per-request override
        use_html5 = request.meta.get("use_html5", self.backend)
        if not use_html5:
            # Disabled globally or explicitly (for this request)
            return response

        # If already HtmlResponse, convert to HtmlFiveResponse
        if isinstance(response, HtmlResponse):
            return response.replace(cls=HtmlFiveResponse).with_backend(use_html5)

        # Check if plain Response should be HTML based on content-type
        content_type_header = response.headers.get("Content-Type", b"")
        if content_type_header:
            content_type = content_type_header.decode("utf-8", errors="ignore").lower()
            if any(ct in content_type for ct in _HTML_CONTENT_TYPES):
                return response.replace(cls=HtmlFiveResponse).with_backend(use_html5)

        # Not an HTML response, pass through unchanged
        return response
