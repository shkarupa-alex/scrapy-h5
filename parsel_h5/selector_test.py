"""Tests for HtmlFiveSelector and HtmlFiveSelectorList."""


from parsel_h5 import HtmlFiveSelector, HtmlFiveSelectorList


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

    def test_create_from_text(self) -> None:
        """Test creating selector from HTML text."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        assert sel is not None
        assert sel.type == "html"

    def test_css_element(self) -> None:
        """Test basic CSS element selector."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("h1")
        assert len(result) == 1
        assert "Hello World" in result.get()

    def test_css_id(self) -> None:
        """Test CSS ID selector."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("#main")
        assert len(result) == 1
        assert "container" in result.get()

    def test_css_class(self) -> None:
        """Test CSS class selector."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css(".intro")
        assert len(result) == 1
        assert "introduction" in result.get()

    def test_css_descendant(self) -> None:
        """Test CSS descendant selector."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("ul a")
        assert len(result) == 3

    def test_css_child(self) -> None:
        """Test CSS child selector."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("ul > li")
        assert len(result) == 3

    def test_css_attribute(self) -> None:
        """Test CSS attribute selector."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a[href]")
        assert len(result) == 3

    def test_css_text_pseudo(self) -> None:
        """Test ::text pseudo-element."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("h1::text")
        assert len(result) == 1
        assert result.get() == "Hello World"

    def test_css_attr_pseudo(self) -> None:
        """Test ::attr() pseudo-element."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)")
        assert len(result) == 3
        hrefs = result.getall()
        assert "/link1" in hrefs
        assert "/link2" in hrefs
        assert "/link3" in hrefs

    def test_getall(self) -> None:
        """Test getall() method."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("li a::text").getall()
        assert result == ["Link 1", "Link 2", "Link 3"]

    def test_get_with_default(self) -> None:
        """Test get() with default value."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("nonexistent").get(default="not found")
        assert result == "not found"

    def test_attrib_property(self) -> None:
        """Test attrib property."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        div = sel.css("#main")
        assert len(div) == 1
        assert div.attrib.get("id") == "main"
        assert "container" in div.attrib.get("class", "")

    def test_re(self) -> None:
        """Test regex extraction."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)").re(r"/link(\d+)")
        assert result == ["1", "2", "3"]

    def test_re_first(self) -> None:
        """Test re_first() method."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)").re_first(r"/link(\d+)")
        assert result == "1"

    def test_re_first_with_default(self) -> None:
        """Test re_first() with default."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a::attr(href)").re_first(r"notfound", default="default")
        assert result == "default"

    def test_bool_true(self) -> None:
        """Test boolean conversion with content."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("h1")
        assert bool(result[0]) is True

    def test_bool_false(self) -> None:
        """Test boolean conversion without content."""
        sel = HtmlFiveSelector(text="<div></div>")
        result = sel.css("div::text")
        # With ::text, we get the element but its text is empty
        # The boolean of the selector should be False when text is empty
        if len(result) > 0:
            assert bool(result[0]) is False
        else:
            # No results is also acceptable
            assert len(result) == 0

    def test_repr(self) -> None:
        """Test string representation."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("h1")
        repr_str = repr(result[0])
        assert "HtmlFiveSelector" in repr_str
        assert "h1" in repr_str

    def test_chained_selectors(self) -> None:
        """Test chaining CSS selectors."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Chain element selectors
        result = sel.css("#main").css("a")
        assert len(result) == 3
        # Then get text from the chain
        texts = result.css("::text").getall()
        assert len(texts) == 3


class TestHtmlFiveSelectorList:
    """Tests for HtmlFiveSelectorList class."""

    SAMPLE_HTML = """
    <ul>
        <li><a href="/a">A</a></li>
        <li><a href="/b">B</a></li>
        <li><a href="/c">C</a></li>
    </ul>
    """

    def test_getitem_single(self) -> None:
        """Test indexing single element."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("li")
        assert isinstance(result[0], HtmlFiveSelector)

    def test_getitem_slice(self) -> None:
        """Test slicing."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("li")
        sliced = result[1:]
        assert isinstance(sliced, HtmlFiveSelectorList)
        assert len(sliced) == 2

    def test_css_on_list(self) -> None:
        """Test CSS on SelectorList."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("li").css("a::text")
        assert result.getall() == ["A", "B", "C"]

    def test_attrib_on_list(self) -> None:
        """Test attrib property on list."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a")
        # Returns first element's attrib
        assert result.attrib.get("href") == "/a"

    def test_attrib_on_empty_list(self) -> None:
        """Test attrib on empty list."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("nonexistent")
        assert result.attrib == {}

    def test_extract_alias(self) -> None:
        """Test extract() is alias for getall()."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a::text")
        assert result.extract() == result.getall()

    def test_extract_first_alias(self) -> None:
        """Test extract_first() is alias for get()."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        result = sel.css("a::text")
        assert result.extract_first() == result.get()

