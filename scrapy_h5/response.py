"""HtmlFiveResponse class extending Scrapy's HtmlResponse with html5 parsing."""

from typing import Any

from scrapy.http import HtmlResponse

from scrapy_h5.selector import HtmlFiveSelector, HtmlFiveSelectorList


class HtmlFiveResponse(HtmlResponse):
    """HtmlResponse subclass that uses html5 for parsing.

    This response class provides the same API as Scrapy's HtmlResponse,
    but uses html5 parser instead of lxml, providing better
    HTML5 compliance.
    """

    _scrapy_h5_backend = None
    _cached_h5_selector: HtmlFiveSelector | None = None

    def with_backend(self, backend: str) -> "HtmlFiveResponse":
        self._scrapy_h5_backend = backend
        return self

    @property
    def selector(self) -> HtmlFiveSelector:
        """Return an HtmlFiveSelector for this response's content.

        The selector is lazily created and cached.
        """
        if self._cached_h5_selector is None:
            self._cached_h5_selector = HtmlFiveSelector(self._scrapy_h5_backend, text=self.text)
        return self._cached_h5_selector

    def xpath(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> HtmlFiveSelectorList:
        """Select elements using XPath (converted to CSS).

        Note: Only common XPath patterns are supported. Complex expressions
        will raise XPathConversionError.
        """
        return self.selector.xpath(query, **kwargs)

    def css(self, query: str) -> HtmlFiveSelectorList:
        """Select elements using CSS selectors.

        Supports standard CSS selectors plus parsel's ::text and ::attr()
        pseudo-elements.
        """
        return self.selector.css(query)
