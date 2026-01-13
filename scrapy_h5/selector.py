"""HtmlFiveSelector and HtmlFiveSelectorList classes for HTML parsing."""

import logging
import re
from collections.abc import Mapping
from re import Pattern
from typing import Any, TypeVar, overload

import markupever
import selectolax.lexbor
from parsel.utils import extract_regex, flatten, iflatten, shorten
from scrapy.utils.trackref import object_ref

_SelectorType = TypeVar("_SelectorType", bound="HtmlFiveSelector")
_SelectorListType = TypeVar("_SelectorListType", bound="HtmlFiveSelectorList")

logger = logging.getLogger(__name__)


class HtmlFiveSelectorList(list[_SelectorType], object_ref):
    """A list of HtmlFiveSelector objects with convenience methods for bulk operations."""

    @overload
    def __getitem__(self, pos: int) -> _SelectorType: ...

    @overload
    def __getitem__(self, pos: slice) -> _SelectorListType: ...

    def __getitem__(self, pos: int | slice) -> _SelectorListType | _SelectorType:
        o = super().__getitem__(pos)
        if isinstance(pos, slice):
            return self.__class__(o)
        return o

    def __getstate__(self) -> None:
        raise TypeError("can't pickle SelectorList objects")

    def jmespath(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> _SelectorListType:
        """Call the `.jmespath()` method for each element in this list."""
        return self.__class__(flatten([x.jmespath(query, **kwargs) for x in self]))

    def xpath(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> _SelectorListType:
        """Apply XPath query (converted to CSS) to all elements and return flattened results."""
        return self.__class__(flatten([x.xpath(query, **kwargs) for x in self]))

    def css(self, query: str) -> _SelectorListType:
        """Apply CSS selector to all elements and return flattened results."""
        return self.__class__(flatten([x.css(query) for x in self]))

    def re(
        self,
        regex: str | Pattern[str],
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> list[str]:
        """Apply regex to all elements and return flattened string results."""
        return flatten([x.re(regex, replace_entities=replace_entities) for x in self])

    @overload
    def re_first(
        self,
        regex: str | Pattern[str],
        default: None = None,
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> str | None: ...

    @overload
    def re_first(
        self,
        regex: str | Pattern[str],
        default: str,
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> str: ...

    def re_first(
        self,
        regex: str | Pattern[str],
        default: str | None = None,
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> str | None:
        """Apply regex and return first match, or default if no match."""
        for el in iflatten(x.re(regex, replace_entities=replace_entities) for x in self):
            return el
        return default

    def getall(self) -> list[str]:
        """Get serialized content of all elements."""
        return [x.get() for x in self]

    extract = getall

    @overload
    def get(self, default: None = None) -> str | None: ...

    @overload
    def get(self, default: str) -> str: ...

    def get(self, default: str | None = None) -> str | None:
        """Get serialized content of first element, or default if empty."""
        for x in self:
            return x.get()
        return default

    extract_first = get

    @property
    def attrib(self) -> Mapping[str, str]:
        """Return attributes of first element, or empty dict if empty."""
        for x in self:
            return x.attrib
        return {}

    def drop(self) -> None:
        """Drop matched nodes from the parent for each element in this list."""
        for x in self:
            x.drop()


class HtmlFiveSelector(object_ref):
    """Selector for HTML parsing.

    Provides a parsel-compatible API for CSS and XPath selectors.
    """

    __slots__ = ["__weakref__", "_attr", "_backend", "_expr", "_root", "_text"]

    selectorlist_cls = HtmlFiveSelectorList

    def __init__(
        self,
        backend: str,
        *,
        text: str | None = None,
        root: selectolax.lexbor.LexborNode | markupever.dom.BaseNode | None = None,
        _expr: str | None = None,
        _text: bool = False,
        _attr: str | None = None,
    ) -> None:
        if backend not in {"lexbor", "html5ever"}:
            raise ValueError(f"Unsupported html5 backend: {backend}")
        self._backend = backend

        if text is None and root is None:
            raise ValueError("At least one of text or root arguments must be provided")
        if text is not None and root is not None:
            raise ValueError("At most one of text or root arguments must be provided")

        if text is not None and not isinstance(text, str):
            raise TypeError(f"Argument `text` should be of type str, got {type(text)}")

        self._expr = _expr
        self._text = _text
        self._attr = _attr

        if text is not None and self._backend == "lexbor":
            # Parse the HTML text with Lexbor
            self._root = selectolax.lexbor.LexborHTMLParser(text).root
        elif text is not None and self._backend == "html5ever":
            # Parse the HTML text with html5ever
            self._root = markupever.parse(text).root()
        else:  # root is not None
            self._root = root

    def jmespath(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> _SelectorListType:
        """Find objects matching the JMESPath `query`."""
        raise NotImplementedError

    def xpath(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> _SelectorListType:
        """Select elements using XPath."""
        raise NotImplementedError

    def css(self, query: str) -> _SelectorListType:
        """Select elements using CSS selector.

        Supports parsel's ::text and ::attr() pseudo-elements.
        """
        results = self.selectorlist_cls()
        for subquery, is_text, attr_name in self._parse_css(query):
            results.extend(self._select_css(subquery, is_text, attr_name))

        return results

    def _parse_css(self, query: str) -> list[tuple[str, bool, str | None]]:
        """Parse CSS query and extract ::text and ::attr() pseudo-elements.

        Handles comma-separated selectors by processing each part.
        Returns: list of (subquery, is_text, attr_name)
        """
        # Handle comma-separated selectors
        if "," in query:
            parts = []
            for part in query.split(","):
                parts.extend(self._parse_css(part.strip()))
            return parts

        is_text = False
        attr_name = None

        # Check for ::text pseudo-element
        if query.endswith("::text"):
            query = query[:-6]
            is_text = True
        # Check for ::attr(name) pseudo-element
        elif match := re.search(r"::attr\(([^)]+)\)$", query):
            query = query[: match.start()]
            attr_name = match.group(1)

        return [(query, is_text, attr_name)]

    def _select_css(self, query: str, is_text: bool, attr_name: str | None) -> list[_SelectorType]:  # noqa: FBT001
        if not query.strip():
            # Apply pseudo-element to current element
            return [
                self.__class__(
                    self._backend,
                    root=self._root,
                    _expr=query,
                    _text=is_text,
                    _attr=attr_name,
                ),
            ]

        elements = (
            self._root.css(query) if isinstance(self._root, selectolax.lexbor.LexborNode) else self._root.select(query)
        )
        return [
            self.__class__(
                self._backend,
                root=el,
                _expr=query,
                _text=is_text,
                _attr=attr_name,
            )
            for el in elements
        ]

    def re(
        self,
        regex: str | Pattern[str],
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> list[str]:
        """Apply regex to the selector content."""
        return extract_regex(regex, self.get(), replace_entities=replace_entities)

    @overload
    def re_first(
        self,
        regex: str | Pattern[str],
        default: None = None,
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> str | None: ...

    @overload
    def re_first(
        self,
        regex: str | Pattern[str],
        default: str,
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> str: ...

    def re_first(
        self,
        regex: str | Pattern[str],
        default: str | None = None,
        replace_entities: bool = True,  # noqa: FBT001, FBT002
    ) -> str | None:
        """Apply regex and return first match."""
        return next(
            iflatten(self.re(regex, replace_entities=replace_entities)),
            default,
        )

    def get(self) -> str:  # noqa: PLR0911
        """Serialize and return the matched node content."""
        if self._text and isinstance(self._root, selectolax.lexbor.LexborNode):
            return self._root.text()
        if self._text and isinstance(self._root, markupever.dom.Element):
            return self._root.text()
        if self._text:
            return ""

        if self._attr and isinstance(self._root, selectolax.lexbor.LexborNode):
            return self._root.attributes.get(self._attr, "")
        if self._attr and isinstance(self._root, markupever.dom.Element):
            return self._root.attrs.get(self._attr, "")
        if self._attr:
            return ""

        if isinstance(self._root, selectolax.lexbor.LexborNode):
            return self._root.html
        if isinstance(self._root, markupever.dom.BaseNode):
            return self._root.serialize()

        return str(self._root)

    extract = get

    def getall(self) -> list[str]:
        """Return the result in a 1-element list."""
        return [self.get()]

    def register_namespace(self, prefix: str, uri: str) -> None:
        """Register a namespace (kept for API compatibility)."""

    def remove_namespaces(self) -> None:
        """Remove namespaces (kept for API compatibility)."""

    def drop(self) -> None:
        """Drop/remove matched nodes from the parent.

        Removes the current element from its parent in the DOM tree.
        After calling drop(), the element is detached and the parent's
        serialized content will no longer include this element.
        """
        if isinstance(self._root, selectolax.lexbor.LexborNode):
            self._root.decompose()
        if isinstance(self._root, markupever.dom.BaseNode):
            self._root.detach()

    @property
    def attrib(self) -> dict[str, str | None]:
        """Return element attributes as a dict."""
        if isinstance(self._root, selectolax.lexbor.LexborNode):
            return self._root.attributes
        if isinstance(self._root, markupever.dom.Element):
            # Convert AttrsList to dict with proper key extraction
            # markupever uses QualName objects as keys, we need the local name
            attrs = self._root.attrs
            return {key.local: attrs.get(key, "") for key in attrs}
        return {}

    def __bool__(self) -> bool:
        """Return True if there is content."""
        return bool(self.get())

    __nonzero__ = __bool__

    def __str__(self) -> str:
        return self.get()

    def __repr__(self) -> str:
        data = repr(shorten(self.get(), width=40))
        return f"<{type(self).__name__} query={self._expr!r} data={data}>"
