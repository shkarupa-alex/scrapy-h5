"""Link extractors using HTML5 parsers (selectolax/lexbor and markupever/html5ever).

This module provides link extraction functionality that works with HTML5-compliant
parsers instead of lxml. It integrates with Scrapy's link extraction framework while
supporting both the lexbor (via selectolax) and html5ever (via markupever) backends.

Example:
    >>> from scrapy_h5.extractor import LinkExtractor
    >>> from scrapy_h5 import HtmlFiveResponse
    >>> response = HtmlFiveResponse(url="http://example.com", body=b'<a href="/page">Link</a>')
    >>> extractor = LinkExtractor()
    >>> links = extractor.extract_links(response)
"""

import operator
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any
from urllib.parse import urljoin

import markupever
import selectolax.lexbor
from parsel import Selector
from scrapy.link import Link
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor, LxmlParserLinkExtractor, _nons, _RegexOrSeveral
from scrapy.utils.misc import rel_has_nofollow
from w3lib.html import strip_html5_whitespace
from w3lib.url import safe_url_string


class LinkExtractor(LxmlLinkExtractor):
    """A link extractor that uses HTML5 parsers for link extraction.

    This class extends Scrapy's LxmlLinkExtractor to work with HTML5-compliant
    parsers (selectolax/lexbor or markupever/html5ever) instead of lxml.

    Unlike the parent class, this extractor does not support `restrict_xpaths`,
    `restrict_css`, or `restrict_text` parameters as it operates directly on
    HTML5-parsed DOM trees.

    Args:
        allow: Regular expression(s) that URLs must match to be extracted.
        deny: Regular expression(s) that URLs must NOT match to be extracted.
        allow_domains: Domain(s) that URLs must belong to.
        deny_domains: Domain(s) that URLs must NOT belong to.
        tags: Tag name(s) to look for when extracting links. Defaults to ('a', 'area').
        attrs: Attribute name(s) to look for in tags. Defaults to ('href',).
        canonicalize: Whether to canonicalize URLs before filtering. Defaults to False.
        unique: Whether to deduplicate extracted links. Defaults to True.
        process_value: Optional callable to process each extracted URL value.
        deny_extensions: File extension(s) to deny. Uses default if None.
        strip: Whether to strip whitespace from URLs. Defaults to True.

    Example:
        >>> extractor = LinkExtractor(
        ...     allow="/products/",
        ...     deny="/admin/",
        ...     tags=["a"],
        ...     attrs=["href"],
        ... )
    """

    def __init__(  # noqa: PLR0913
        self,
        allow: _RegexOrSeveral = (),
        deny: _RegexOrSeveral = (),
        allow_domains: str | Iterable[str] = (),
        deny_domains: str | Iterable[str] = (),
        tags: str | Iterable[str] = ("a", "area"),
        attrs: str | Iterable[str] = ("href",),
        canonicalize: bool = False,  # noqa: FBT001, FBT002
        unique: bool = True,  # noqa: FBT001, FBT002
        process_value: Callable[[Any], Any] | None = None,
        deny_extensions: str | Iterable[str] | None = None,
        strip: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        super().__init__(
            allow=allow,
            deny=deny,
            allow_domains=allow_domains,
            deny_domains=deny_domains,
            restrict_xpaths=(),
            tags=tags,
            attrs=attrs,
            canonicalize=canonicalize,
            unique=unique,
            process_value=process_value,
            deny_extensions=deny_extensions,
            restrict_css=(),
            strip=strip,
            restrict_text=None,
        )
        self.link_extractor = HtmlFiveParserLinkExtractor(
            tag=partial(operator.contains, tags),
            attr=partial(operator.contains, attrs),
            unique=unique,
            process=process_value,
            strip=strip,
            canonicalized=not canonicalize,
        )


class HtmlFiveParserLinkExtractor(LxmlParserLinkExtractor):
    """Low-level link parser that extracts links from HTML5-parsed DOM trees.

    This class extends Scrapy's LxmlParserLinkExtractor to iterate over
    HTML5-parsed DOM nodes (from selectolax/lexbor or markupever/html5ever)
    instead of lxml etree elements.

    It overrides the `_iter_links` method to traverse the DOM tree and yield
    (element, attribute_name, attribute_value) tuples for matching tags/attrs.

    This class is used internally by LinkExtractor and typically should not
    be instantiated directly.
    """

    def _extract_links(
        self,
        selector: Selector,
        response_url: str,
        response_encoding: str,
        base_url: str,
    ) -> list[Link]:
        """Extract links from the selector's root document.

        This overrides the parent method to handle HTML5 element types
        (selectolax LexborNode and markupever Element) instead of lxml elements.

        Args:
            selector: A selector object with a `root` attribute pointing to the DOM tree.
            response_url: The URL of the response being processed.
            response_encoding: The character encoding of the response.
            base_url: The base URL for resolving relative links.

        Returns:
            A list of Link objects extracted from the document.
        """
        links: list[Link] = []
        for el, _attr, attr_val in self._iter_links(selector.root):
            try:
                if self.strip:
                    attr_val = strip_html5_whitespace(attr_val)  # noqa: PLW2901
                attr_val = urljoin(base_url, attr_val)  # noqa: PLW2901
            except ValueError:
                continue  # skipping bogus links
            else:
                url = self.process_attr(attr_val)
                if url is None:
                    continue
            try:
                url = safe_url_string(url, encoding=response_encoding)
            except ValueError:
                continue

            # to fix relative links after process_value
            url = urljoin(response_url, url)
            link = Link(
                url,
                self._get_element_text(el),
                nofollow=rel_has_nofollow(self._get_element_attr(el, "rel")),
            )
            links.append(link)
        return self._deduplicate_if_needed(links)

    def _get_element_text(
        self,
        el: selectolax.lexbor.LexborNode | markupever.dom.BaseNode,
    ) -> str:
        """Get the text content of an element.

        Args:
            el: The element to extract text from.

        Returns:
            The text content of the element, or empty string if none.
        """
        if isinstance(el, selectolax.lexbor.LexborNode):
            return el.text()
        if isinstance(el, markupever.dom.Element):
            return el.text()
        return ""

    def _get_element_attr(
        self,
        el: selectolax.lexbor.LexborNode | markupever.dom.BaseNode,
        attr: str,
    ) -> str | None:
        """Get an attribute value from an element.

        Args:
            el: The element to get the attribute from.
            attr: The attribute name.

        Returns:
            The attribute value, or None if not present.
        """
        if isinstance(el, selectolax.lexbor.LexborNode):
            return el.attributes.get(attr)
        if isinstance(el, markupever.dom.Element):
            return el.attrs.get(attr)
        return None

    def _iter_links(
        self,
        document: selectolax.lexbor.LexborNode | markupever.dom.BaseNode,
    ) -> Iterable[tuple[selectolax.lexbor.LexborNode | markupever.dom.BaseNode, str, str]]:
        """Iterate over links in the document.

        Dispatches to the appropriate backend-specific method based on document type.

        Args:
            document: The root node of the HTML5-parsed document tree.
                Can be either a selectolax LexborNode or markupever BaseNode.

        Yields:
            Tuples of (element, attribute_name, attribute_value) for each link found.

        Raises:
            TypeError: If document is not a supported node type.
        """
        if isinstance(document, selectolax.lexbor.LexborNode):
            yield from self._iter_links_lexbor(document)
        elif isinstance(document, markupever.dom.BaseNode):
            yield from self._iter_links_html5ever(document)
        else:
            raise TypeError(f"Unsupported document type: {type(document)}")

    def _iter_links_lexbor(
        self,
        document: selectolax.lexbor.LexborNode,
    ) -> Iterable[tuple[selectolax.lexbor.LexborNode, str, str]]:
        """Iterate over links in a selectolax/lexbor document.

        Traverses the DOM tree and yields link elements matching the configured
        tag and attribute filters.

        Args:
            document: The root LexborNode to traverse.

        Yields:
            Tuples of (element, attribute_name, attribute_value) for each link.
        """
        for el in document.traverse():
            if not self.scan_tag(_nons(el.tag)):
                continue
            attribs = el.attributes
            for attrib in attribs:
                if not self.scan_attr(attrib):
                    continue
                yield el, attrib, attribs[attrib]

    def _iter_links_html5ever(
        self,
        document: markupever.dom.BaseNode,
    ) -> Iterable[tuple[markupever.dom.BaseNode, str, str]]:
        """Iterate over links in a markupever/html5ever document.

        Traverses the DOM tree and yields link elements matching the configured
        tag and attribute filters.

        Args:
            document: The root BaseNode to traverse.

        Yields:
            Tuples of (element, attribute_name, attribute_value) for each link.
        """
        for edge in document.traverse():
            # Skip closed edges (only process opening traversal)
            if edge.closed:
                continue
            # EdgeTraverse wraps nodes - get the actual node
            el = edge.node
            if not isinstance(el, markupever.dom.Element):
                continue
            if not self.scan_tag(_nons(el.name.local)):
                continue
            attribs = el.attrs
            for attrib in attribs:
                if not self.scan_attr(attrib.local):
                    continue
                yield el, attrib, attribs[attrib]
