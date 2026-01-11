"""Scrapy Downloader Middleware for html5ever-based HTML parsing."""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from scrapy import signals
from scrapy.http import HtmlResponse

from parsel_h5.response import HtmlFiveResponse

if TYPE_CHECKING:
    from scrapy import Request, Spider
    from scrapy.crawler import Crawler
    from scrapy.http import Response

logger = logging.getLogger(__name__)


class HtmlFiveResponseMiddleware:
    """Downloader Middleware that replaces HtmlResponse with HtmlFiveResponse.

    This middleware intercepts HTML responses and replaces them with
    HtmlFiveResponse instances, which use html5ever for parsing instead of lxml.

    Settings:
        HTML5_ENABLED: bool (default: True)
            Global enable/disable for html5ever parsing.

    Per-request control:
        Set request.meta['use_html5'] = False to disable for a specific request.
        Set request.meta['use_html5'] = True to force enable (overrides HTML5_ENABLED=False).

    Usage in settings.py:
        DOWNLOADER_MIDDLEWARES = {
            'parsel_h5.HtmlFiveResponseMiddleware': 543,
        }
        HTML5_ENABLED = True  # optional, True by default
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> HtmlFiveResponseMiddleware:
        """Create middleware instance from crawler settings."""
        enabled = crawler.settings.getbool("HTML5_ENABLED", default=True)
        middleware = cls(enabled=enabled)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider: Spider) -> None:
        """Log when spider opens."""
        spider.logger.debug(
            "HtmlFiveResponseMiddleware enabled=%s (html5ever parsing for HTML responses)",
            self.enabled,
        )

    def process_response(
        self,
        request: Request,
        response: Response,
        spider: Spider,
    ) -> Response:
        """Process response and optionally replace with HtmlFiveResponse.

        Only HtmlResponse instances are replaced. Other response types
        (XmlResponse, JsonResponse, TextResponse, etc.) pass through unchanged.
        """
        # Check if this is an HTML response
        if not isinstance(response, HtmlResponse):
            return response

        # Already an HtmlFiveResponse (shouldn't happen, but be safe)
        if isinstance(response, HtmlFiveResponse):
            return response

        # Check per-request override
        use_html5 = request.meta.get("use_html5")
        if use_html5 is False:
            # Explicitly disabled for this request
            return response
        if use_html5 is True:
            # Explicitly enabled for this request
            pass
        elif not self.enabled:
            # Global setting is disabled and no per-request override
            return response

        # Replace with HtmlFiveResponse
        try:
            return response.replace(cls=HtmlFiveResponse)
        except Exception as e:
            # If replacement fails for any reason, return original response
            logger.exception(
                "Failed to replace response with HtmlFiveResponse for %s: %s",
                request.url,
                e,
            )
            return response
