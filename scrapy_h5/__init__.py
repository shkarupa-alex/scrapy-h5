"""scrapy-h5: HTML5 parsing for Scrapy.

This package provides Scrapy integration for html5-based HTML parsing.

Main components:
- HtmlFiveSelector: Selector class using html5 for parsing
- HtmlFiveSelectorList: List of HtmlFiveSelector instances
- HtmlFiveResponse: Scrapy response class with HtmlFiveSelector
- HtmlFiveResponseMiddleware: Scrapy Downloader Middleware for automatic html5 parsing
- LinkExtractor: Link extractor using HTML5 parsers

Usage:
    # In settings.py
    DOWNLOADER_MIDDLEWARES = {
        'scrapy_h5.HtmlFiveResponseMiddleware': 543,
    }

    # In spider
    def parse(self, response):
        # CSS selectors work directly
        titles = response.css('h1::text').getall()

        # Common XPath patterns are converted to CSS
        links = response.xpath('//a/@href').getall()

    # Using LinkExtractor
    from scrapy_h5 import LinkExtractor
    extractor = LinkExtractor(allow=r'/products/')
    links = extractor.extract_links(response)
"""

from scrapy_h5.extractor import LinkExtractor
from scrapy_h5.middleware import HtmlFiveResponseMiddleware
from scrapy_h5.response import HtmlFiveResponse
from scrapy_h5.selector import (
    HtmlFiveSelector,
    HtmlFiveSelectorList,
)

__all__ = [
    "HtmlFiveResponse",
    "HtmlFiveResponseMiddleware",
    "HtmlFiveSelector",
    "HtmlFiveSelectorList",
    "LinkExtractor",
]

__version__ = "0.1.0"
