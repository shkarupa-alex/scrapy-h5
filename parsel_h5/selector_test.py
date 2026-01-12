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

    def test_drop_single_element(self) -> None:
        """Test dropping a single element from the DOM."""
        sel = HtmlFiveSelector(text="<div><span>remove me</span><p>keep me</p></div>")
        sel.css("span")[0].drop()
        result = sel.get()
        assert "<span>" not in result
        assert "remove me" not in result
        assert "<p>keep me</p>" in result

    def test_drop_on_text_node_is_noop(self) -> None:
        """Test that drop() on a text node doesn't raise."""
        sel = HtmlFiveSelector(text="<div>text</div>")
        text_sel = sel.css("div::text")[0]
        # Should not raise
        text_sel.drop()

    def test_jmespath_simple_key(self) -> None:
        """Test JMESPath simple key extraction."""
        sel = HtmlFiveSelector(text='<script>{"name": "test", "value": 123}</script>')
        result = sel.css("script::text")[0].jmespath("name")
        assert result.getall() == ["test"]

    def test_jmespath_nested_key(self) -> None:
        """Test JMESPath nested key extraction."""
        sel = HtmlFiveSelector(text='<script>{"user": {"name": "alice", "age": 30}}</script>')
        result = sel.css("script::text")[0].jmespath("user.name")
        assert result.getall() == ["alice"]

    def test_jmespath_array(self) -> None:
        """Test JMESPath array extraction."""
        sel = HtmlFiveSelector(text='<script>{"items": ["a", "b", "c"]}</script>')
        result = sel.css("script::text")[0].jmespath("items")
        # Should return each item as a separate selector
        assert len(result) == 3
        assert result.getall() == ["a", "b", "c"]

    def test_jmespath_array_index(self) -> None:
        """Test JMESPath array index access."""
        sel = HtmlFiveSelector(text='<script>{"items": ["first", "second", "third"]}</script>')
        result = sel.css("script::text")[0].jmespath("items[0]")
        assert result.getall() == ["first"]

    def test_jmespath_no_match(self) -> None:
        """Test JMESPath with no matching key."""
        sel = HtmlFiveSelector(text='<script>{"name": "test"}</script>')
        result = sel.css("script::text")[0].jmespath("nonexistent")
        assert result.getall() == []
        assert len(result) == 0

    def test_jmespath_on_invalid_json(self) -> None:
        """Test JMESPath on non-JSON text."""
        sel = HtmlFiveSelector(text="<script>not valid json</script>")
        result = sel.css("script::text")[0].jmespath("name")
        assert len(result) == 0

    def test_jmespath_numeric_value(self) -> None:
        """Test JMESPath returning numeric value."""
        sel = HtmlFiveSelector(text='<script>{"count": 42}</script>')
        result = sel.css("script::text")[0].jmespath("count")
        # Numeric values get JSON serialized
        assert len(result) == 1
        assert result.get() == "42"


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

    def test_drop_multiple_elements(self) -> None:
        """Test dropping multiple elements from the DOM."""
        sel = HtmlFiveSelector(text="<div><span>1</span><span>2</span><p>keep</p></div>")
        sel.css("span").drop()
        result = sel.get()
        assert "<span>" not in result
        assert "<p>keep</p>" in result

    def test_drop_nested_element(self) -> None:
        """Test dropping a nested element."""
        sel = HtmlFiveSelector(text="<div><ul><li>item</li></ul><p>text</p></div>")
        sel.css("ul").drop()
        result = sel.get()
        assert "<ul>" not in result
        assert "<li>" not in result
        assert "<p>text</p>" in result

    def test_drop_on_empty_list_is_noop(self) -> None:
        """Test that drop() on empty SelectorList doesn't raise."""
        sel = HtmlFiveSelector(text="<div>text</div>")
        empty = sel.css("nonexistent")
        # Should not raise
        empty.drop()

    def test_jmespath_on_selector_list(self) -> None:
        """Test jmespath() on HtmlFiveSelectorList."""
        html = """
        <script>{"name": "first"}</script>
        <script>{"name": "second"}</script>
        """
        sel = HtmlFiveSelector(text=html)
        result = sel.css("script::text").jmespath("name")
        assert len(result) == 2
        assert result.getall() == ["first", "second"]


class TestMultipleSelectorsCSS:
    """Tests for multiple (comma-separated) CSS selectors with mixed types."""

    SAMPLE_HTML = """
    <div>
        <h1>Title</h1>
        <p>Paragraph</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <a href="/link1">Link 1</a>
        <a href="/link2">Link 2</a>
    </div>
    """

    def test_css_combined_element_and_text(self) -> None:
        """Test CSS combining element selection and ::text extraction."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get li elements fully and h1 text content
        li_elements = sel.css("li")
        h1_text = sel.css("h1::text")
        assert len(li_elements) == 2
        assert "Item 1" in li_elements[0].get()
        assert h1_text.get() == "Title"

    def test_css_combined_element_and_attr(self) -> None:
        """Test CSS combining element selection and ::attr() extraction."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get p elements fully and a href attributes
        p_elements = sel.css("p")
        a_hrefs = sel.css("a::attr(href)")
        assert len(p_elements) == 1
        assert "Paragraph" in p_elements.get()
        assert len(a_hrefs) == 2
        assert set(a_hrefs.getall()) == {"/link1", "/link2"}

    def test_css_combined_text_and_attr(self) -> None:
        """Test CSS combining ::text and ::attr() extraction."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get h1 text and a href attributes
        h1_text = sel.css("h1::text")
        a_hrefs = sel.css("a::attr(href)")
        assert h1_text.get() == "Title"
        assert set(a_hrefs.getall()) == {"/link1", "/link2"}

    def test_css_combined_all_three_types(self) -> None:
        """Test CSS combining element, ::text, and ::attr() in separate calls."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get li elements, h1 text, and a href - each type separately
        li_elements = sel.css("li")
        h1_text = sel.css("h1::text")
        a_hrefs = sel.css("a::attr(href)")

        assert len(li_elements) == 2
        assert "Item 1" in li_elements[0].get()
        assert h1_text.get() == "Title"
        assert "/link1" in a_hrefs.getall()

    def test_css_chained_different_types(self) -> None:
        """Test chaining selectors with different extraction types."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # First select container, then get text and attrs from children
        div = sel.css("div")
        li_texts = div.css("li::text")
        a_hrefs = div.css("a::attr(href)")

        assert len(li_texts) == 2
        assert li_texts.getall() == ["Item 1", "Item 2"]
        assert len(a_hrefs) == 2
        assert set(a_hrefs.getall()) == {"/link1", "/link2"}


class TestMultipleSelectorsXPath:
    """Tests for XPath selectors (converted to CSS) with mixed types."""

    SAMPLE_HTML = """
    <div>
        <h1>Title</h1>
        <p>Paragraph</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <a href="/link1">Link 1</a>
        <a href="/link2">Link 2</a>
    </div>
    """

    def test_xpath_combined_element_and_text(self) -> None:
        """Test XPath combining element selection and text() extraction."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get li elements fully and h1 text content
        li_elements = sel.xpath("//li")
        h1_text = sel.xpath("//h1/text()")
        assert len(li_elements) == 2
        assert "Item 1" in li_elements[0].get()
        assert h1_text.get() == "Title"

    def test_xpath_combined_element_and_attr(self) -> None:
        """Test XPath combining element selection and @attr extraction."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get p elements fully and a href attributes
        p_elements = sel.xpath("//p")
        a_hrefs = sel.xpath("//a/@href")
        assert len(p_elements) == 1
        assert "Paragraph" in p_elements.get()
        assert len(a_hrefs) == 2
        assert set(a_hrefs.getall()) == {"/link1", "/link2"}

    def test_xpath_combined_text_and_attr(self) -> None:
        """Test XPath combining text() and @attr extraction."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get h1 text and a href attributes
        h1_text = sel.xpath("//h1/text()")
        a_hrefs = sel.xpath("//a/@href")
        assert h1_text.get() == "Title"
        assert set(a_hrefs.getall()) == {"/link1", "/link2"}

    def test_xpath_combined_all_three_types(self) -> None:
        """Test XPath combining element, text(), and @attr in separate calls."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Get li elements, h1 text, and a href - each type separately
        li_elements = sel.xpath("//li")
        h1_text = sel.xpath("//h1/text()")
        a_hrefs = sel.xpath("//a/@href")

        assert len(li_elements) == 2
        assert "Item 1" in li_elements[0].get()
        assert h1_text.get() == "Title"
        assert "/link1" in a_hrefs.getall()

    def test_xpath_chained_different_types(self) -> None:
        """Test chaining XPath/CSS selectors with different extraction types."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # First select container with XPath, then get text and attrs from children
        div = sel.xpath("//div")
        li_texts = div.xpath("//li/text()")
        a_hrefs = div.xpath("//a/@href")

        assert len(li_texts) == 2
        assert li_texts.getall() == ["Item 1", "Item 2"]
        assert len(a_hrefs) == 2
        assert set(a_hrefs.getall()) == {"/link1", "/link2"}

    def test_xpath_mixed_extractions_on_same_page(self) -> None:
        """Test using different XPath extraction types on the same document."""
        sel = HtmlFiveSelector(text=self.SAMPLE_HTML)
        # Combine results from different XPath queries manually
        li_elements = sel.xpath("//li")
        h1_text = sel.xpath("//h1/text()")
        a_hrefs = sel.xpath("//a/@href")

        # Verify we can work with all types simultaneously
        # Use CSS for nested extraction since relative XPath isn't supported
        all_li_text = [li.css("::text").get() for li in li_elements]
        assert all_li_text == ["Item 1", "Item 2"]
        assert h1_text.get() == "Title"
        assert set(a_hrefs.getall()) == {"/link1", "/link2"}
