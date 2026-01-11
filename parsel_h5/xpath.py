"""XPath to CSS converter for common patterns.

This module provides conversion of common XPath expressions to CSS selectors.
Complex XPath expressions that cannot be converted will raise XPathConversionError.
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


# Pattern matchers for XPath expressions
# These patterns handle common XPath constructs

# Match //element or /element
_ELEMENT_PATTERN = re.compile(r"^/{1,2}([a-zA-Z_][a-zA-Z0-9_-]*)$")

# Match //*[@id='value'] or //element[@id='value']
_ID_PATTERN = re.compile(r"^/{1,2}(\*|[a-zA-Z_][a-zA-Z0-9_-]*)\[@id\s*=\s*['\"]([^'\"]+)['\"]\]$")

# Match //*[@class='value'] or //element[@class='value']
_CLASS_PATTERN = re.compile(r"^/{1,2}(\*|[a-zA-Z_][a-zA-Z0-9_-]*)\[@class\s*=\s*['\"]([^'\"]+)['\"]\]$")

# Match //element[@attr] - has attribute
_HAS_ATTR_PATTERN = re.compile(r"^/{1,2}([a-zA-Z_][a-zA-Z0-9_-]*)\[@([a-zA-Z_][a-zA-Z0-9_-]*)\]$")

# Match //element[@attr='value']
_ATTR_VALUE_PATTERN = re.compile(
    r"^/{1,2}([a-zA-Z_][a-zA-Z0-9_-]*)\[@([a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*['\"]([^'\"]+)['\"]\]$",
)

# Match //element/text()
_TEXT_PATTERN = re.compile(r"^(.*)/text\(\)$")

# Match //element/@attr
_ATTR_EXTRACT_PATTERN = re.compile(r"^(.*)/@([a-zA-Z_][a-zA-Z0-9_-]*)$")

# Match path expressions like //div/p or //div//p
_PATH_PATTERN = re.compile(r"^(/{1,2})([a-zA-Z_*][a-zA-Z0-9_-]*)(.*)$")


def _convert_simple_path(xpath: str) -> str:
    """Convert a simple path expression (no predicates, text(), or @attr)."""
    if not xpath:
        return ""

    parts: list[str] = []
    remaining = xpath

    while remaining:
        # Match next path segment
        match = _PATH_PATTERN.match(remaining)
        if not match:
            # Check if it's just an element name at the end
            if re.match(r"^[a-zA-Z_*][a-zA-Z0-9_-]*$", remaining):
                parts.append(remaining)
                break
            msg = f"Cannot parse path segment: {remaining}"
            raise XPathConversionError(xpath, msg)

        slashes, element, rest = match.groups()

        # // means descendant (space in CSS), / means child (> in CSS)
        if parts:  # Not the first element
            if slashes == "//":
                parts.append(" ")  # descendant combinator
            else:
                parts.append(" > ")  # child combinator

        parts.append(element)
        remaining = rest

    return "".join(parts)


def _convert_with_predicate(xpath: str) -> ConversionResult:
    """Convert XPath with predicates like [@id='x'] or [@class='y']."""
    # Try ID pattern
    if match := _ID_PATTERN.match(xpath):
        element, id_value = match.groups()
        if element == "*":
            return ConversionResult(css=f"#{id_value}")
        return ConversionResult(css=f"{element}#{id_value}")

    # Try class pattern
    if match := _CLASS_PATTERN.match(xpath):
        element, class_value = match.groups()
        # Handle multiple classes (space-separated in XPath value)
        classes = ".".join(class_value.split())
        if element == "*":
            return ConversionResult(css=f".{classes}")
        return ConversionResult(css=f"{element}.{classes}")

    # Try has-attribute pattern
    if match := _HAS_ATTR_PATTERN.match(xpath):
        element, attr = match.groups()
        return ConversionResult(css=f"{element}[{attr}]")

    # Try attribute=value pattern
    if match := _ATTR_VALUE_PATTERN.match(xpath):
        element, attr, value = match.groups()
        return ConversionResult(css=f'{element}[{attr}="{value}"]')

    msg = "Unsupported predicate pattern"
    raise XPathConversionError(
        xpath,
        msg,
        suggestion="Use CSS selectors directly, e.g., 'div#id', 'div.class', 'a[href]'",
    )


def xpath_to_css(xpath: str) -> tuple[str, bool, bool, str | None]:
    """Convert XPath to CSS selector.

    Args:
        xpath: The XPath expression to convert.

    Returns:
        Tuple of (css_selector, is_text, is_attr, attr_name)

    Raises:
        XPathConversionError: If the XPath cannot be converted.
    """
    xpath = xpath.strip()
    is_text = False
    is_attr = False
    attr_name: str | None = None

    # Check for text() at the end
    if match := _TEXT_PATTERN.match(xpath):
        xpath = match.group(1)
        is_text = True

    # Check for /@attr at the end
    if match := _ATTR_EXTRACT_PATTERN.match(xpath):
        xpath = match.group(1)
        attr_name = match.group(2)
        is_attr = True

    # Now convert the remaining xpath
    xpath = xpath.strip()

    # Empty after stripping text()/attr
    if not xpath:
        return ("*", is_text, is_attr, attr_name)

    # Try simple element pattern: //div or /div
    if match := _ELEMENT_PATTERN.match(xpath):
        return (match.group(1), is_text, is_attr, attr_name)

    # Try patterns with predicates
    try:
        result = _convert_with_predicate(xpath)
        return (result.css, is_text or result.is_text, is_attr or result.is_attr, attr_name or result.attr_name)
    except XPathConversionError:
        pass

    # Try path expressions: //div/p, //div//span, etc.
    # First check if there are unsupported features
    unsupported_patterns = [
        (r"\[position\(\)", "position() function"),
        (r"\[last\(\)", "last() function"),
        (r"\[contains\(", "contains() function"),
        (r"\[starts-with\(", "starts-with() function"),
        (r"\[not\(", "not() function"),
        (r"following-sibling::", "following-sibling axis"),
        (r"preceding-sibling::", "preceding-sibling axis"),
        (r"ancestor::", "ancestor axis"),
        (r"parent::", "parent axis"),
        (r"\[.*\s+and\s+.*\]", "and operator in predicates"),
        (r"\[.*\s+or\s+.*\]", "or operator in predicates"),
        (r"\[\d+\]", "positional predicates like [1] or [2]"),
    ]

    for pattern, description in unsupported_patterns:
        if re.search(pattern, xpath, re.IGNORECASE):
            raise XPathConversionError(
                xpath,
                f"{description} is not supported",
                suggestion="Use CSS selectors with :nth-child(), :first-child, etc., or process results in Python",
            )

    # Try to parse as a path expression
    try:
        css = _convert_simple_path(xpath)
        return (css, is_text, is_attr, attr_name)
    except XPathConversionError:
        pass

    # If we get here, we couldn't convert
    raise XPathConversionError(
        xpath,
        "Complex XPath expression not supported",
        suggestion="Use CSS selectors directly for better html5ever compatibility",
    )

