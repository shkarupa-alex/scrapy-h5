"""HtmlFiveSelector and HtmlFiveSelectorList classes using markupever (html5ever) for HTML parsing."""

from __future__ import annotations
import json
import logging
import re
from typing import TYPE_CHECKING, Any, TypeVar, cast, overload

import jmespath
import markupever
from parsel.selector import CannotRemoveElementWithoutRoot, _load_json_or_none
from parsel.utils import extract_regex, flatten, iflatten, shorten
from scrapy.utils.trackref import object_ref

from parsel_h5.xpath import xpath_to_css

if TYPE_CHECKING:
    from collections.abc import Mapping
    from re import Pattern

    from typing_extensions import Self

_SelectorType = TypeVar("_SelectorType", bound="HtmlFiveSelector")

logger = logging.getLogger(__name__)


class HtmlFiveSelectorList(list[_SelectorType], object_ref):
    """A list of HtmlFiveSelector objects with convenience methods for bulk operations."""

    @overload
    def __getitem__(self, pos: int) -> _SelectorType: ...

    @overload
    def __getitem__(self, pos: slice) -> Self: ...

    def __getitem__(self, pos: int | slice) -> _SelectorType | Self:
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
    ) -> Self:
        """Call the `.jmespath()` method for each element in this list.

        Return their results flattened as another `HtmlFiveSelectorList`.

        `query` is the same argument as the one in `HtmlFiveSelector.jmespath`.

        Any additional named arguments are passed to the underlying `jmespath.search` call, e.g.::

            selector.jmespath("author.name", options=jmespath.Options(dict_cls=collections.OrderedDict))
        """
        return self.__class__(flatten([x.jmespath(query, **kwargs) for x in self]))

    def xpath(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> Self:
        """Apply XPath query (converted to CSS) to all elements and return flattened results."""
        return self.__class__(flatten([x.xpath(query, **kwargs) for x in self]))

    def css(self, query: str) -> Self:
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
    """Selector using markupever (html5ever) for HTML parsing.

    Provides a parsel-compatible API for CSS and XPath selectors.
    """

    __slots__ = ["__weakref__", "_attr_name", "_expr", "_is_attr", "_is_text", "_root", "_text", "namespaces", "type"]

    selectorlist_cls = HtmlFiveSelectorList["HtmlFiveSelector"]

    def __init__(
        self,
        text: str | None = None,
        root: markupever.dom.Element | markupever.dom.TreeDom | str | None = None,
        _expr: str | None = None,
        _is_text: bool = False,
        _is_attr: bool = False,
        _attr_name: str | None = None,
        type: str = "html",  # noqa: A002
        namespaces: Mapping[str, str] | None = None,
    ) -> None:
        if text is None and root is None:
            raise ValueError("Selector needs text or root arguments")

        if text is not None and not isinstance(text, str):
            raise TypeError(f"Argument `text` should be of type str, got {text.__class__}")

        if type != "html":
            raise TypeError("HtmlFiveSelector only accepts html")

        self.type = type
        self.namespaces = dict(namespaces) if namespaces else {}
        self._expr = _expr
        self._is_text = _is_text
        self._is_attr = _is_attr
        self._attr_name = _attr_name

        if text is not None:
            # Parse the HTML text
            self._root = markupever.parse(text)
            self._text = text
        elif root is not None:
            if isinstance(root, str):
                # Text node
                self._root = root
                self._text = root
            else:
                self._root = root
                self._text = None
        else:
            raise ValueError("HtmlFiveSelector requires either text or root argument")

    def _parse_css_pseudo(self, query: str) -> tuple[str, bool, bool, str | None]:
        """Parse CSS query and extract ::text and ::attr() pseudo-elements.

        Handles comma-separated selectors by processing each part.
        Returns: (cleaned_query, is_text, is_attr, attr_name)
        """
        is_text = False
        is_attr = False
        attr_name = None

        # Handle comma-separated selectors
        if "," in query:
            parts = []
            for part in query.split(","):
                part = part.strip()
                cleaned, part_is_text, part_is_attr, part_attr = self._parse_css_pseudo(part)
                parts.append(cleaned)
                # Use the flags from any part (they should be consistent)
                is_text = is_text or part_is_text
                is_attr = is_attr or part_is_attr
                if part_attr:
                    attr_name = part_attr
            return ", ".join(parts), is_text, is_attr, attr_name

        # Check for ::text pseudo-element
        if query.endswith("::text"):
            query = query[:-6]
            is_text = True
        # Check for ::attr(name) pseudo-element
        elif match := re.search(r"::attr\(([^)]+)\)$", query):
            attr_name = match.group(1)
            query = query[: match.start()]
            is_attr = True

        return query, is_text, is_attr, attr_name

    def jmespath(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> HtmlFiveSelectorList[Self]:
        """Find objects matching the JMESPath `query`.

        Return the res  # noqa: ANN401
        List elements implement `HtmlFiveSelector` interface too.

        `query` is a string containing the `JMESPath <https://jmespath.org/>` query to apply.

        Any additional named arguments are passed to the underlying `jmespath.search` call, e.g.:

            selector.jmespath("author.name", options=jmespath.Options(dict_cls=collections.OrderedDict))
        """
        data = self._get_jmespath_data()
        result = self._run_jmespath_query(query, data, **kwargs)
        return cast("HtmlFiveSelectorList[_SelectorType]", self.selectorlist_cls(result))

    def _get_jmespath_data(self) -> Any:  # noqa: ANN401
        """Get data for JMESPath query from the current root."""
        if isinstance(self._root, str):
            # Root is a string (text node or JSON string)
            return _load_json_or_none(self._root)
        if hasattr(self._root, "text"):
            # Element with text() method
            return _load_json_or_none(self._root.text())
        # TreeDom - serialize and try to parse
        if hasattr(self._root, "serialize"):
            return _load_json_or_none(self._root.serialize())
        return None

    def _run_jmespath_query(
        self,
        query: str,
        data: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> list[Self]:
        """Run JMESPath query on data and return list of selectors."""
        result = jmespath.search(query, data, **kwargs)
        if result is None:
            return []
        if not isinstance(result, list):
            result = [result]
        return [self._make_jmespath_selector(x, query) for x in result]

    def _make_jmespath_selector(
        self,
        value: Any,  # noqa: ANN401
        query: str,
    ) -> Self:
        """Create a selector from a JMESPath result value."""
        if isinstance(value, str):
            # Return as text node selector
            return self.__class__(root=value, _expr=query)
        # Non-string values (dicts, lists, etc.) - convert to JSON string
        return self.__class__(root=json.dumps(value), _expr=query)

    def xpath(
        self,
        query: str,
        namespaces: Mapping[str, str] | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> HtmlFiveSelectorList[Self]:
        """Select elements using XPath (converted to CSS).

        Only common XPath patterns are supported. Complex expressions will raise an error.
        """
        css_query, is_text, is_attr, attr_name = xpath_to_css(query)

        # Parse pseudo-elements from CSS if any
        clean_query, css_is_text, css_is_attr, css_attr_name = self._parse_css_pseudo(css_query)

        # Combine flags from xpath conversion and css parsing
        final_is_text = is_text or css_is_text
        final_is_attr = is_attr or css_is_attr
        final_attr_name = attr_name or css_attr_name

        results: list[Self] = []

        if isinstance(self._root, str):
            return self.selectorlist_cls(results)

        try:
            if isinstance(self._root, markupever.dom.TreeDom) or hasattr(self._root, "select"):
                elements = self._root.select(clean_query) if clean_query else []
            else:
                elements = []
        except ValueError as e:
            # Invalid selector (after XPath conversion)
            logger.warning("Invalid selector after XPath conversion '%s' -> '%s': %s", query, clean_query, e)
            return self.selectorlist_cls(results)
        except Exception as e:
            logger.exception("Unexpected error in XPath selection '%s': %s", query, e)
            return self.selectorlist_cls(results)

        for el in elements:
            selector = self.__class__(
                root=el,
                _expr=query,
                _is_text=final_is_text,
                _is_attr=final_is_attr,
                _attr_name=final_attr_name,
                type=self.type,
                namespaces=self.namespaces,
            )
            results.append(selector)

        return self.selectorlist_cls(results)

    def css(self, query: str) -> HtmlFiveSelectorList[Self]:
        """Select elements using CSS selector.

        Supports parsel's ::text and ::attr() pseudo-elements.
        """
        # Parse pseudo-elements
        clean_query, is_text, is_attr, attr_name = self._parse_css_pseudo(query)

        results: list[Self] = []

        # Get the actual element to select from
        if isinstance(self._root, str):
            # Can't select from a text node
            return self.selectorlist_cls(results)

        # Handle case where query is just ::text or ::attr() (for chained selectors)
        if not clean_query.strip():
            # Apply pseudo-element to current element
            selector = self.__class__(
                root=self._root,
                _expr=query,
                _is_text=is_text,
                _is_attr=is_attr,
                _attr_name=attr_name,
                type=self.type,
                namespaces=self.namespaces,
            )
            return self.selectorlist_cls([selector])

        try:
            if isinstance(self._root, markupever.dom.TreeDom) or hasattr(self._root, "select"):
                elements = self._root.select(clean_query)
            else:
                elements = []
        except ValueError as e:
            # Invalid CSS selector
            logger.warning("Invalid CSS selector '%s': %s", query, e)
            return self.selectorlist_cls(results)
        except Exception as e:
            # Catch any unexpected markupever exceptions
            logger.exception("Unexpected error in CSS selection '%s': %s", query, e)
            return self.selectorlist_cls(results)

        for el in elements:
            selector = self.__class__(
                root=el,
                _expr=query,
                _is_text=is_text,
                _is_attr=is_attr,
                _attr_name=attr_name,
                type=self.type,
                namespaces=self.namespaces,
            )
            results.append(selector)

        return self.selectorlist_cls(results)

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

    def get(self) -> str:
        """Serialize and return the matched node content."""
        if self._is_text:
            # Return text content
            return self._get_text()
        if self._is_attr and self._attr_name:
            # Return attribute value
            return self._get_attr(self._attr_name)
        if isinstance(self._root, str):
            return self._root
        if isinstance(self._root, markupever.dom.TreeDom):
            return self._root.serialize()
        if hasattr(self._root, "serialize"):
            return self._root.serialize()
        return str(self._root)

    extract = get

    def _get_text(self) -> str:
        """Get text content of the element."""
        if isinstance(self._root, str):
            return self._root
        if hasattr(self._root, "text"):
            return self._root.text()
        return ""

    def _get_attr(self, name: str) -> str:
        """Get attribute value from the element."""
        if isinstance(self._root, str):
            return ""
        if hasattr(self._root, "attrs"):
            return self._root.attrs.get(name, "")
        return ""

    def getall(self) -> list[str]:
        """Return the result in a 1-element list."""
        return [self.get()]

    def register_namespace(self, prefix: str, uri: str) -> None:
        """Register a namespace (no-op for html5ever, kept for API compatibility)."""
        self.namespaces[prefix] = uri

    def remove_namespaces(self) -> None:
        """Remove namespaces (no-op for html5ever, kept for API compatibility)."""

    def drop(self) -> None:
        """Drop/remove matched nodes from the parent.

        Removes the current element from its parent in the DOM tree.
        After calling drop(), the element is detached and the parent's
        serialized content will no longer include this element.
        """
        self._root.detach()

    @property
    def attrib(self) -> dict[str, str]:
        """Return element attributes as a dict."""
        if isinstance(self._root, str):
            return {}
        if hasattr(self._root, "attrs"):
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
