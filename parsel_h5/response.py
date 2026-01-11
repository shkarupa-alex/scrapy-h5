"""HtmlFiveResponse class extending Scrapy's HtmlResponse with html5ever parsing."""

from __future__ import annotations
import logging
from typing import Any, cast

from scrapy.http import HtmlResponse

from parsel_h5.selector import HtmlFiveSelector, HtmlFiveSelectorList

logger = logging.getLogger(__name__)


class HtmlFiveResponse(HtmlResponse):
    """HtmlResponse subclass that uses html5ever (via markupever) for parsing.

    This response class provides the same API as Scrapy's HtmlResponse,
    but uses html5ever for HTML parsing instead of lxml, providing better
    HTML5 compliance.
    """

    _cached_h5_selector: HtmlFiveSelector | None = None

    @property
    def selector(self) -> HtmlFiveSelector:
        """Return an HtmlFiveSelector for this response's content.

        The selector is lazily created and cached.
        """
        if self._cached_h5_selector is None:
            self._cached_h5_selector = HtmlFiveSelector(text=self.text)
        return self._cached_h5_selector

    def xpath(self, query: str, **kwargs: Any) -> HtmlFiveSelectorList:
        """Select elements using XPath (converted to CSS).

        Note: Only common XPath patterns are supported. Complex expressions
        will raise XPathConversionError.
        """
        return cast("HtmlFiveSelectorList", self.selector.xpath(query, **kwargs))

    def css(self, query: str) -> HtmlFiveSelectorList:
        """Select elements using CSS selectors.

        Supports standard CSS selectors plus parsel's ::text and ::attr()
        pseudo-elements.
        """
        return cast("HtmlFiveSelectorList", self.selector.css(query))
