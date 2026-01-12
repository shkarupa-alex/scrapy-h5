"""XPath to CSS converter for common patterns.

This module provides conversion of common XPath expressions to CSS selectors.
Complex XPath expressions that cannot be converted will raise XPathConversionError.

Supports ::text and ::attr() pseudo-elements via is_text/is_attr return values.
"""

from __future__ import annotations
import re
from dataclasses import dataclass


class XPathConversionError(ValueError):
    """Raised when an XPath expression cannot be converted to CSS."""

    def __init__(self, xpath: str, reason: str, suggestion: str | None = None) -> None:
        self.xpath = xpath
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Cannot convert XPath '{xpath}': {reason}"
        if suggestion:
            msg += f". Suggestion: {suggestion}"
        super().__init__(msg)


@dataclass
class ConversionResult:
    """Result of XPath to CSS conversion."""

    css: str
    is_text: bool = False
    is_attr: bool = False
    attr_name: str | None = None


# ============================================================================
# Regex patterns for XPath parsing (inspired by cssfy.py)
# ============================================================================

# Base patterns
_TAG = r"([a-zA-Z_][a-zA-Z0-9_-]*|\*)"
_ATTR_NAME = r"@([a-zA-Z_][a-zA-Z0-9_-]*)"
_QUOTED_VALUE = r"""['"]([-\w\s/:.#,;]+)['"]"""

# Match id(value) or id("value") or id('value')
_ID_FUNC_PATTERN = re.compile(r"^id\(['\"]?([^'\")\s]+)['\"]?\)(.*)$")

# Match //element or /element with optional predicates
_NODE_PATTERN = re.compile(
    rf"""
    ^(?P<nav>//?)                           # // or /
    (?P<tag>{_TAG[1:-1]})                   # tag name or *
    (?:\[(?P<predicate>[^\]]+)\])?          # optional predicate [...]
    (?:\[(?P<nth>\d+)\])?                   # optional nth [n]
    (?P<rest>.*)$                           # remaining path
    """,
    re.VERBOSE,
)

# Predicate patterns
_PRED_ID = re.compile(rf"^{_ATTR_NAME}\s*=\s*{_QUOTED_VALUE}$".replace(r"([a-zA-Z_][a-zA-Z0-9_-]*)", "id"))
_PRED_CLASS = re.compile(rf"^{_ATTR_NAME}\s*=\s*{_QUOTED_VALUE}$".replace(r"([a-zA-Z_][a-zA-Z0-9_-]*)", "class"))
_PRED_ATTR_EQ = re.compile(rf"^{_ATTR_NAME}\s*=\s*{_QUOTED_VALUE}$")
_PRED_HAS_ATTR = re.compile(rf"^{_ATTR_NAME}$")
_PRED_CONTAINS_ATTR = re.compile(rf"^contains\(\s*{_ATTR_NAME}\s*,\s*{_QUOTED_VALUE}\)$")
_PRED_STARTS_WITH_ATTR = re.compile(rf"^starts-with\(\s*{_ATTR_NAME}\s*,\s*{_QUOTED_VALUE}\)$")
_PRED_TEXT_EQ = re.compile(rf"^(?:text\(\)|\.)\s*=\s*{_QUOTED_VALUE}$")
_PRED_CONTAINS_TEXT = re.compile(rf"^contains\(\s*(?:text\(\)|\.)\s*,\s*{_QUOTED_VALUE}\)$")

# Pattern for text node extraction (e.g. //div/text())
_TEXT_PATTERN = re.compile(r"^(.*)/text\(\)$")

# Pattern for attribute extraction (e.g. //a/@href)
_ATTR_EXTRACT_PATTERN = re.compile(r"^(.*)/@([a-zA-Z_][a-zA-Z0-9_-]*)$")


def _convert_predicate(predicate: str, xpath: str) -> tuple[str, str | None]:  # noqa: PLR0911
    """Convert a single predicate expression to CSS.

    Args:
        predicate: The predicate content (without brackets)
        xpath: Original xpath for error messages

    Returns:
        Tuple of (CSS selector fragment, nth-of-type value or None)

    Raises:
        XPathConversionError: If predicate cannot be converted
    """
    predicate = predicate.strip()

    # Numeric position [1], [2], etc. -> :nth-of-type(n)
    if predicate.isdigit():
        return ("", predicate)

    # @attr="value" patterns -> #id, .class, or [attr="value"]
    if match := _PRED_ATTR_EQ.match(predicate):
        attr, value = match.groups()
        if attr == "id":
            return ("#" + value.replace(" ", "#"), None)
        if attr == "class":
            return ("." + value.replace(" ", "."), None)
        return (f'[{attr}="{value}"]', None)

    # @attr -> [attr]
    if match := _PRED_HAS_ATTR.match(predicate):
        return (f"[{match.group(1)}]", None)

    # contains(@attr, "value") -> [attr*=value]
    if match := _PRED_CONTAINS_ATTR.match(predicate):
        attr, value = match.groups()
        return (f"[{attr}*={value}]", None)

    # starts-with(@attr, "value") -> [attr^=value]
    if match := _PRED_STARTS_WITH_ATTR.match(predicate):
        attr, value = match.groups()
        return (f"[{attr}^={value}]", None)

    # text()="value" - NOT supported in standard CSS
    if _PRED_TEXT_EQ.match(predicate):
        raise XPathConversionError(
            xpath,
            "Text matching predicates are not supported in CSS",
            suggestion="Select elements first, then filter by text content in Python",
        )

    # contains(text(), "value") - NOT supported in standard CSS
    if _PRED_CONTAINS_TEXT.match(predicate):
        raise XPathConversionError(
            xpath,
            "Text contains predicates are not supported in CSS",
            suggestion="Select elements first, then filter by text content in Python",
        )

    # Check for other unsupported patterns
    _check_unsupported(predicate, xpath)

    raise XPathConversionError(
        xpath,
        f"Unsupported predicate: [{predicate}]",
        suggestion="Use CSS selectors directly for better html5ever compatibility",
    )


def _check_unsupported(xpath: str, original_xpath: str) -> None:
    """Check for unsupported XPath patterns and raise descriptive errors."""
    unsupported = [
        (r"position\(\)", "position() function"),
        (r"last\(\)", "last() function"),
        (r"not\(", "not() function"),
        (r"following-sibling::", "following-sibling axis"),
        (r"preceding-sibling::", "preceding-sibling axis"),
        (r"ancestor::", "ancestor axis"),
        (r"parent::", "parent axis"),
        (r"\s+and\s+", "and operator in predicates"),
        (r"\s+or\s+", "or operator in predicates"),
    ]

    for pattern, description in unsupported:
        if re.search(pattern, xpath, re.IGNORECASE):
            raise XPathConversionError(
                original_xpath,
                f"{description} is not supported",
                suggestion="Use CSS selectors or process results in Python",
            )


def _convert_node(  # noqa: PLR0913
    nav: str,
    tag: str,
    predicate: str | None,
    nth: str | None,
    *,
    is_first: bool,
    xpath: str,
) -> str:
    """Convert a single node (element with optional predicate) to CSS.

    Args:
        nav: Navigation type ('/' or '//')
        tag: Element tag name or '*'
        predicate: Optional predicate content (without brackets)
        nth: Optional position number
        is_first: Whether this is the first node in the path
        xpath: Original xpath for error messages

    Returns:
        CSS selector fragment
    """
    parts: list[str] = []

    # Add combinator (space for //, > for /) - except for first element
    if not is_first:
        if nav == "//":
            parts.append(" ")  # descendant combinator
        else:
            parts.append(" > ")  # child combinator

    # Tag name (* is represented as empty in CSS for most cases)
    if tag != "*":
        parts.append(tag)

    # Convert predicate if present
    pred_nth: str | None = None
    if predicate:
        css_pred, pred_nth = _convert_predicate(predicate, xpath)
        parts.append(css_pred)

    # Position -> :nth-of-type(n)
    # Can come from predicate conversion or explicit nth group
    final_nth = nth or pred_nth
    if final_nth:
        parts.append(f":nth-of-type({final_nth})")

    return "".join(parts)


def _parse_and_convert(xpath: str) -> str:
    """Parse and convert an XPath expression to CSS.

    Handles complex paths like //div[@id="x"]/span[@class="y"]//a[2]
    """
    original = xpath
    css_parts: list[str] = []
    is_first = True
    remaining = xpath

    # Check for id() function at the start
    if match := _ID_FUNC_PATTERN.match(remaining):
        id_value = match.group(1)
        rest = match.group(2)
        css_parts.append(f"#{id_value}")
        is_first = False
        remaining = rest

    while remaining:
        # Try to match next node
        match = _NODE_PATTERN.match(remaining)
        if not match:
            # Maybe just trailing whitespace
            if remaining.strip() == "":
                break
            raise XPathConversionError(
                original,
                f"Cannot parse: {remaining}",
                suggestion="Use CSS selectors directly",
            )

        nav = match.group("nav")
        tag = match.group("tag")
        predicate = match.group("predicate")
        nth = match.group("nth")
        rest = match.group("rest")

        # Convert this node
        node_css = _convert_node(nav, tag, predicate, nth, is_first=is_first, xpath=original)
        css_parts.append(node_css)

        is_first = False
        remaining = rest

    return "".join(css_parts).strip()


def xpath_to_css(xpath: str) -> tuple[str, bool, bool, str | None]:
    """Convert XPath to CSS selector.

    Supports common XPath patterns including:
    - Basic elements: //div, /html/body
    - ID selectors: //div[@id='x'], //*[@id='x'], id('x')
    - Class selectors: //div[@class='x y'], //*[@class='x']
    - Attribute selectors: //a[@href], //a[@href='x']
    - Attribute contains: //a[contains(@href, 'x')] -> [href*=x]
    - Attribute starts-with: //a[starts-with(@href, 'http')] -> [href^=http]
    - Position selectors: //li[2] -> li:nth-of-type(2)
    - Path expressions: //div/p, //div//span
    - Text extraction: //p/text() (returns is_text=True)
    - Attribute extraction: //a/@href (returns is_attr=True, attr_name='href')

    Args:
        xpath: The XPath expression to convert.

    Returns:
        Tuple of (css_selector, is_text, is_attr, attr_name)
        - css_selector: The converted CSS selector
        - is_text: True if /text() was present (use ::text pseudo-element)
        - is_attr: True if /@attr was present (use ::attr() pseudo-element)
        - attr_name: The attribute name if is_attr is True

    Raises:
        XPathConversionError: If the XPath cannot be converted.
    """
    xpath = xpath.strip()
    is_text = False
    is_attr = False
    attr_name: str | None = None

    # Check for text() at the end: //div/text()
    if match := _TEXT_PATTERN.match(xpath):
        xpath = match.group(1)
        is_text = True

    # Check for /@attr at the end: //a/@href
    if match := _ATTR_EXTRACT_PATTERN.match(xpath):
        xpath = match.group(1)
        attr_name = match.group(2)
        is_attr = True

    xpath = xpath.strip()

    # Empty after stripping text()/attr
    if not xpath:
        return ("*", is_text, is_attr, attr_name)

    # Check for unsupported patterns before attempting conversion
    _check_unsupported(xpath, xpath)

    # Convert the xpath
    try:
        css = _parse_and_convert(xpath)
    except XPathConversionError:
        raise
    except Exception as e:
        raise XPathConversionError(
            xpath,
            f"Conversion failed: {e}",
            suggestion="Use CSS selectors directly for html5ever compatibility",
        ) from e
    else:
        return (css, is_text, is_attr, attr_name)
