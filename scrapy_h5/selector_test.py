"""Tests for HtmlFiveSelector and HtmlFiveSelectorList."""

import pytest

from scrapy_h5 import HtmlFiveSelector, HtmlFiveSelectorList


class TestHtmlFiveSelector:
    """Tests for HtmlFiveSelector class."""

    SAMPLE_HTML = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <div id="main" class="container primary">
            <h1>Hello World</h1>
            <p class="intro">This is an introduction.</p>
            <ul>
                <li><a href="/link1">Link 1</a></li>
                <li><a href="/link2">Link 2</a></li>
                <li><a href="/link3">Link 3</a></li>
            </ul>
        </div>
        <div id="footer">
            <p>Footer text</p>
        </div>
    </body>
    </html>
    """

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_create_from_text(self, backend: str) -> None:
        """Test creating selector from HTML text."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        assert sel is not None

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_xpath(self, backend: str) -> None:
        """Test xpath() metod."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        try:
            sel.xpath("//li")
            raise AssertionError
        except NotImplementedError:
            pass

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_element(self, backend: str) -> None:
        """Test basic CSS element selector."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("h1")
        assert len(result) == 1
        assert "Hello World" in result.get()

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_id(self, backend: str) -> None:
        """Test CSS ID selector."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("#main")
        assert len(result) == 1
        assert "container" in result.get()

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_class(self, backend: str) -> None:
        """Test CSS class selector."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css(".intro")
        assert len(result) == 1
        assert "introduction" in result.get()

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_descendant(self, backend: str) -> None:
        """Test CSS descendant selector."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("ul a")
        assert len(result) == 3  # noqa: PLR2004

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_child(self, backend: str) -> None:
        """Test CSS child selector."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("ul > li")
        assert len(result) == 3  # noqa: PLR2004

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_attribute(self, backend: str) -> None:
        """Test CSS attribute selector."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a[href]")
        assert len(result) == 3  # noqa: PLR2004

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_text_pseudo(self, backend: str) -> None:
        """Test ::text pseudo-element."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("h1::text")
        assert len(result) == 1
        assert result.get() == "Hello World"

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_attr_pseudo(self, backend: str) -> None:
        """Test ::attr() pseudo-element."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)")
        assert len(result) == 3  # noqa: PLR2004
        hrefs = result.getall()
        assert "/link1" in hrefs
        assert "/link2" in hrefs
        assert "/link3" in hrefs

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_getall(self, backend: str) -> None:
        """Test getall() method."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("li a::text").getall()
        assert result == ["Link 1", "Link 2", "Link 3"]

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_get_with_default(self, backend: str) -> None:
        """Test get() with default value."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("nonexistent").get(default="not found")
        assert result == "not found"

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_attrib_property(self, backend: str) -> None:
        """Test attrib property."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        div = sel.css("#main")
        assert len(div) == 1
        assert div.attrib.get("id") == "main"
        assert "container" in div.attrib.get("class", "")

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_re(self, backend: str) -> None:
        """Test regex extraction."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)").re(r"/link(\d+)")
        assert result == ["1", "2", "3"]

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_re_first(self, backend: str) -> None:
        """Test re_first() method."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)").re_first(r"/link(\d+)")
        assert result == "1"

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_re_first_with_default(self, backend: str) -> None:
        """Test re_first() with default."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)").re_first(r"notfound", default="default")
        assert result == "default"

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_bool_true(self, backend: str) -> None:
        """Test boolean conversion with content."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("h1")
        assert bool(result[0]) is True

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_bool_false(self, backend: str) -> None:
        """Test boolean conversion without content."""
        sel = HtmlFiveSelector(backend, text="<div></div>")
        result = sel.css("div::text")
        # With ::text, we get the element but its text is empty
        # The boolean of the selector should be False when text is empty
        if len(result) > 0:
            assert bool(result[0]) is False
        else:
            # No results is also acceptable
            assert len(result) == 0

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_repr(self, backend: str) -> None:
        """Test string representation."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("h1")
        repr_str = repr(result[0])
        assert "HtmlFiveSelector" in repr_str
        assert "h1" in repr_str

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_chained_selectors(self, backend: str) -> None:
        """Test chaining CSS selectors."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        # Chain element selectors
        result = sel.css("#main").css("a")
        assert len(result) == 3  # noqa: PLR2004
        # Then get text from the chain
        texts = result.css("::text").getall()
        assert len(texts) == 3  # noqa: PLR2004

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_drop_single_element(self, backend: str) -> None:
        """Test dropping a single element from the DOM."""
        sel = HtmlFiveSelector(backend, text="<div><span>remove me</span><p>keep me</p></div>")
        sel.css("span")[0].drop()
        result = sel.get()
        assert "<span>" not in result
        assert "remove me" not in result
        assert "<p>keep me</p>" in result

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_drop_on_text_node_is_noop(self, backend: str) -> None:
        """Test that drop() on a text node doesn't raise."""
        sel = HtmlFiveSelector(backend, text="<div>text</div>")
        text_sel = sel.css("div::text")[0]
        # Should not raise
        text_sel.drop()


class TestHtmlFiveSelectorList:
    """Tests for HtmlFiveSelectorList class."""

    SAMPLE_HTML = """
    <ul>
        <li><a href="/a">A</a></li>
        <li><a href="/b">B</a></li>
        <li><a href="/c">C</a></li>
    </ul>
    """

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_getitem_single(self, backend: str) -> None:
        """Test indexing single element."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("li")
        assert isinstance(result[0], HtmlFiveSelector)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_getitem_slice(self, backend: str) -> None:
        """Test slicing."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("li")
        sliced = result[1:]
        assert isinstance(sliced, HtmlFiveSelectorList)
        assert len(sliced) == 2  # noqa: PLR2004

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_on_list(self, backend: str) -> None:
        """Test CSS on SelectorList."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("li").css("a::text")
        assert result.getall() == ["A", "B", "C"]

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_attrib_on_list(self, backend: str) -> None:
        """Test attrib property on list."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a")
        # Returns first element's attrib
        assert result.attrib.get("href") == "/a"

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_attrib_on_empty_list(self, backend: str) -> None:
        """Test attrib on empty list."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("nonexistent")
        assert result.attrib == {}

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_alias(self, backend: str) -> None:
        """Test extract() is alias for getall()."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a::text")
        assert result.extract() == result.getall()

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_first_alias(self, backend: str) -> None:
        """Test extract_first() is alias for get()."""
        sel = HtmlFiveSelector(backend, text=self.SAMPLE_HTML)
        result = sel.css("a::text")
        assert result.extract_first() == result.get()

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_drop_multiple_elements(self, backend: str) -> None:
        """Test dropping multiple elements from the DOM."""
        sel = HtmlFiveSelector(backend, text="<div><span>1</span><span>2</span><p>keep</p></div>")
        sel.css("span").drop()
        result = sel.get()
        assert "<span>" not in result
        assert "<p>keep</p>" in result

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_drop_nested_element(self, backend: str) -> None:
        """Test dropping a nested element."""
        sel = HtmlFiveSelector(backend, text="<div><ul><li>item</li></ul><p>text</p></div>")
        sel.css("ul").drop()
        result = sel.get()
        assert "<ul>" not in result
        assert "<li>" not in result
        assert "<p>text</p>" in result

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_drop_on_empty_list_is_noop(self, backend: str) -> None:
        """Test that drop() on empty SelectorList doesn't raise."""
        sel = HtmlFiveSelector(backend, text="<div>text</div>")
        empty = sel.css("nonexistent")
        # Should not raise
        empty.drop()
