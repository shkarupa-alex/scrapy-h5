"""Tests for XPath to CSS converter."""

import pytest

from parsel_h5.xpath import XPathConversionError, xpath_to_css


class TestXPathToCss:
    """Tests for xpath_to_css function."""

    def test_simple_element(self) -> None:
        """Test //element pattern."""
        css, is_text, is_attr, attr_name = xpath_to_css("//div")
        assert css == "div"
        assert is_text is False
        assert is_attr is False
        assert attr_name is None

    def test_single_slash_element(self) -> None:
        """Test /element pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("/html")
        assert css == "html"

    def test_id_selector_star(self) -> None:
        """Test //*[@id='x'] pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//*[@id='main']")
        assert css == "#main"

    def test_id_selector_element(self) -> None:
        """Test //div[@id='x'] pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//div[@id='container']")
        assert css == "div#container"

    def test_class_selector_star(self) -> None:
        """Test //*[@class='x'] pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//*[@class='active']")
        assert css == ".active"

    def test_class_selector_element(self) -> None:
        """Test //span[@class='x'] pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//span[@class='highlight']")
        assert css == "span.highlight"

    def test_has_attribute(self) -> None:
        """Test //element[@attr] pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//a[@href]")
        assert css == "a[href]"

    def test_attribute_value(self) -> None:
        """Test //element[@attr='value'] pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//a[@href='/home']")
        assert css == 'a[href="/home"]'

    def test_text_extraction(self) -> None:
        """Test //element/text() pattern."""
        css, is_text, is_attr, _attr_name = xpath_to_css("//p/text()")
        assert css == "p"
        assert is_text is True
        assert is_attr is False

    def test_attr_extraction(self) -> None:
        """Test //element/@attr pattern."""
        css, is_text, is_attr, attr_name = xpath_to_css("//a/@href")
        assert css == "a"
        assert is_text is False
        assert is_attr is True
        assert attr_name == "href"

    def test_descendant_path(self) -> None:
        """Test //div//p pattern (descendant)."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//div//p")
        assert css == "div p"

    def test_child_path(self) -> None:
        """Test //div/p pattern (child)."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//div/p")
        assert css == "div > p"

    def test_complex_path(self) -> None:
        """Test //div//ul/li pattern."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("//div//ul/li")
        assert css == "div ul > li"

    def test_path_with_text(self) -> None:
        """Test //div/p/text() pattern."""
        css, is_text, _is_attr, _attr_name = xpath_to_css("//div/p/text()")
        assert css == "div > p"
        assert is_text is True

    def test_path_with_attr(self) -> None:
        """Test //ul/li/a/@href pattern."""
        css, _is_text, is_attr, attr_name = xpath_to_css("//ul/li/a/@href")
        assert css == "ul > li > a"
        assert is_attr is True
        assert attr_name == "href"

    def test_whitespace_handling(self) -> None:
        """Test whitespace in xpath is handled."""
        css, _is_text, _is_attr, _attr_name = xpath_to_css("  //div  ")
        assert css == "div"


class TestXPathConversionError:
    """Tests for unsupported XPath patterns."""

    def test_position_function(self) -> None:
        """Test position() function raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//li[position()=1]")
        assert "position()" in str(exc_info.value)

    def test_last_function(self) -> None:
        """Test last() function raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//li[last()]")
        assert "last()" in str(exc_info.value)

    def test_contains_function(self) -> None:
        """Test contains() function raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//div[contains(@class, 'active')]")
        assert "contains()" in str(exc_info.value)

    def test_starts_with_function(self) -> None:
        """Test starts-with() function raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//a[starts-with(@href, 'http')]")
        assert "starts-with()" in str(exc_info.value)

    def test_not_function(self) -> None:
        """Test not() function raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//div[not(@class)]")
        assert "not()" in str(exc_info.value)

    def test_following_sibling_axis(self) -> None:
        """Test following-sibling axis raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//div/following-sibling::p")
        assert "following-sibling" in str(exc_info.value)

    def test_preceding_sibling_axis(self) -> None:
        """Test preceding-sibling axis raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//div/preceding-sibling::p")
        assert "preceding-sibling" in str(exc_info.value)

    def test_ancestor_axis(self) -> None:
        """Test ancestor axis raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//p/ancestor::div")
        assert "ancestor" in str(exc_info.value)

    def test_parent_axis(self) -> None:
        """Test parent axis raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//p/parent::div")
        assert "parent" in str(exc_info.value)

    def test_positional_predicate(self) -> None:
        """Test positional predicates raise error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//li[1]")
        assert "positional" in str(exc_info.value).lower()

    def test_and_operator(self) -> None:
        """Test and operator raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//div[@class='a' and @id='b']")
        assert "and" in str(exc_info.value)

    def test_or_operator(self) -> None:
        """Test or operator raises error."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//div[@class='a' or @class='b']")
        assert "or" in str(exc_info.value)

    def test_error_has_suggestion(self) -> None:
        """Test that error includes suggestion."""
        with pytest.raises(XPathConversionError) as exc_info:
            xpath_to_css("//li[1]")
        error = exc_info.value
        assert error.suggestion is not None
        assert "CSS" in error.suggestion or "css" in error.suggestion.lower()
