"""Integration test with real Scrapy spider."""

from typing import Any

import pytest
from scrapy import Request, Spider
from scrapy.http import Response

from scrapy_h5 import HtmlFiveResponse, HtmlFiveResponseMiddleware


class SimpleSpider(Spider):
    """Simple spider that extracts document title."""

    name = "simple"
    custom_settings = {  # noqa: RUF012
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_h5.HtmlFiveResponseMiddleware": 650,
        },
    }

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self.collected_items = []

    def parse(self, response: Response, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """Parse response and extract title."""
        title = response.css("title::text").get()
        self.collected_items.append({"url": response.url, "title": title})


@pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
def test_real_spider_with_scrapy_h5_backend(backend: str) -> None:
    """Test a real Scrapy spider using HtmlFiveResponseMiddleware."""
    spider = SimpleSpider()
    middleware = HtmlFiveResponseMiddleware(backend=backend)

    # Start with a regular Response (as Scrapy does initially)
    base_response = Response(
        url="http://example.com",
        body=b"<html><head><title>Test Page</title></head><body>Content</body></html>",
        headers={"Content-Type": "text/html"},
    )

    # Process through middleware
    request = Request(base_response.url, callback=spider.parse)
    result = middleware.process_response(request, base_response)

    assert isinstance(result, HtmlFiveResponse)
    spider.parse(result)
    assert len(spider.collected_items) == 1
    assert spider.collected_items[0]["title"] == "Test Page"
