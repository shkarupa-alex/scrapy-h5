"""parsel-h5: Parsel with html5ever parser for HTML.

This package provides Scrapy integration for html5ever-based HTML parsing
via the markupever Python package.

Main components:
- HtmlFiveSelector: Selector class using html5ever for parsing
- HtmlFiveSelectorList: List of HtmlFiveSelector instances
- HtmlFiveResponse: Scrapy response class with HtmlFiveSelector
- HtmlFiveResponseMiddleware: Scrapy Downloader Middleware for automatic html5ever parsing

Usage:
    # In settings.py
    DOWNLOADER_MIDDLEWARES = {
        'parsel_h5.HtmlFiveResponseMiddleware': 543,
    }

    # In spider
    def parse(self, response):
        # CSS selectors work directly
        titles = response.css('h1::text').getall()

        # Common XPath patterns are converted to CSS
        links = response.xpath('//a/@href').getall()
"""

from parsel_h5.middleware import HtmlFiveResponseMiddleware
from parsel_h5.response import HtmlFiveResponse
from parsel_h5.selector import (
    HtmlFiveParseError,
    HtmlFiveSelectError,
    HtmlFiveSelector,
    HtmlFiveSelectorError,
    HtmlFiveSelectorList,
)
from parsel_h5.xpath import XPathConversionError

__all__ = [
    "HtmlFiveParseError",
    "HtmlFiveResponse",
    "HtmlFiveResponseMiddleware",
    "HtmlFiveSelectError",
    "HtmlFiveSelector",
    "HtmlFiveSelectorError",
    "HtmlFiveSelectorList",
    "XPathConversionError",
]

__version__ = "0.1.0"
