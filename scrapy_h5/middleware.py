"""Scrapy Downloader Middleware for html5-based HTML parsing."""

import logging

from scrapy import Request, Spider, signals
from scrapy.crawler import Crawler
from scrapy.http import HtmlResponse, Response

from scrapy_h5.response import HtmlFiveResponse

logger = logging.getLogger(__name__)


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

        Only HtmlResponse instances are replaced. Other response types
        (XmlResponse, JsonResponse, TextResponse, etc.) pass through unchanged.
        """
        # Check if this is an HTML response
        if not isinstance(response, HtmlResponse):
            return response

        # Check per-request override
        use_html5 = request.meta.get("use_html5", self.backend)
        if use_html5 is None:
            # Disabled globally or explicitly (for this request)
            return response

        # Replace with HtmlFiveResponse
        return response.replace(cls=HtmlFiveResponse).with_backend(use_html5)
