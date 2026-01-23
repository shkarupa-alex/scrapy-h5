"""Integration test with real Scrapy spider."""

from typing import Any

import pytest
from scrapy import Request, Spider
from scrapy.http import Response
from scrapy.spiders import CrawlSpider, Rule

from scrapy_h5 import HtmlFiveResponse, HtmlFiveResponseMiddleware, LinkExtractor


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


class SimpleCrawlSpider(CrawlSpider):
    """Simple crawl spider using LinkExtractor."""

    name = "simple_crawl"
    custom_settings = {  # noqa: RUF012
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_h5.HtmlFiveResponseMiddleware": 650,
        },
    }

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self.collected_items = []

    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def parse_item(self, response: Response, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """Parse item from response."""
        title = response.css("h1::text").get()
        self.collected_items.append({"url": response.url, "title": title})


@pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
def test_crawl_spider_with_link_extractor(backend: str) -> None:
    """Test CrawlSpider using LinkExtractor with HtmlFiveResponse."""
    spider = SimpleCrawlSpider()
    middleware = HtmlFiveResponseMiddleware(backend=backend)

    # Create HTML response with links
    html_body = b"""
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Main Page</h1>
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <a href="https://example.com/external">External</a>
    </body>
    </html>
    """

    base_response = Response(
        url="http://example.com",
        body=html_body,
        headers={"Content-Type": "text/html"},
    )

    # Process through middleware
    request = Request(base_response.url, callback=spider.parse_item)
    result = middleware.process_response(request, base_response)

    # Should be HtmlFiveResponse
    assert isinstance(result, HtmlFiveResponse)

    # Extract links using LinkExtractor
    link_extractor = LinkExtractor()
    links = link_extractor.extract_links(result)

    # Should extract all 3 links
    assert len(links) == 3
    assert links[0].url == "http://example.com/page1"
    assert links[1].url == "http://example.com/page2"
    assert links[2].url == "https://example.com/external"

    # Parse the response
    spider.parse_item(result)
    assert len(spider.collected_items) == 1
    assert spider.collected_items[0]["title"] == "Main Page"
    assert spider.collected_items[0]["url"] == "http://example.com"
