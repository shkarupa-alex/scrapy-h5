"""Scrapy Downloader Middleware for html5-based HTML parsing."""

from scrapy import Request, Spider, signals
from scrapy.crawler import Crawler
from scrapy.http import HtmlResponse, Response, TextResponse
from scrapy.responsetypes import responsetypes

from scrapy_h5.response import HtmlFiveResponse


class HtmlFiveResponseMiddleware:
    """Downloader Middleware that replaces HtmlResponse with HtmlFiveResponse.

    This middleware intercepts HTML responses and replaces them with
    HtmlFiveResponse instances, which use html5 for parsing instead of lxml.

    Settings:
        SCRAPY_H5_BACKEND: str | None (default: 'lexbor')
            Global enable/disable for html5 parsing.

    Per-request control:
        Set request.meta['scrapy_h5_backend'] = False to disable for a specific request.
        Set request.meta['scrapy_h5_backend'] = 'html5ever' to force enable (overrides SCRAPY_H5_BACKEND=False).

    Usage in settings.py:
        DOWNLOADER_MIDDLEWARES = {
            'scrapy_h5.HtmlFiveResponseMiddleware': 650,
        }
        SCRAPY_H5_BACKEND = 'html5ever'  # optional, 'lexbor' by default
    """

    def __init__(self, *, backend: str | None = "lexbor") -> None:
        if backend not in {"lexbor", "html5ever", None}:
            raise ValueError(f"Unsupported html5 backend: {backend}")
        self.backend = backend

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "HtmlFiveResponseMiddleware":
        """Create middleware instance from crawler settings."""
        backend = crawler.settings.get("SCRAPY_H5_BACKEND", default="lexbor")
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
        """Process response and optionally replace with HtmlFiveResponse."""
        # Check per-request override
        scrapy_h5_backend = request.meta.get("scrapy_h5_backend", self.backend)
        if not scrapy_h5_backend:
            # Disabled globally or explicitly (for this request)
            return response

        # Only these types of response can be possibly parsed with HTML parser
        if not isinstance(response, (Response, TextResponse, HtmlResponse)):
            return response

        guess_type = responsetypes.from_args(response.headers, response.url, None, response.body)
        if isinstance(response, HtmlResponse) or guess_type is HtmlResponse:
            return response.replace(cls=HtmlFiveResponse).with_backend(scrapy_h5_backend)

        # Not an HTML response, pass through unchanged
        return response
