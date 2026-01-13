import operator
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

import markupever
import selectolax.lexbor
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor, LxmlParserLinkExtractor, _nons, _RegexOrSeveral


class CssLinkExtractor(LxmlLinkExtractor):
    _csstranslator = None

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
    def _iter_links(
        self,
        document: selectolax.lexbor.LexborNode | markupever.dom.BaseNode,
    ) -> Iterable[tuple[selectolax.lexbor.LexborNode | markupever.dom.BaseNode, str, str]]:
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
        for el in document.traverse():
            if not isinstance(el, markupever.dom.Element):
                continue
            if not self.scan_tag(_nons(el.name.local)):
                continue
            attribs = el.attrs
            for attrib in attribs:
                if not self.scan_attr(attrib.local):
                    continue
                yield el, attrib, attribs[attrib]
