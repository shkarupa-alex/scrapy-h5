"""Tests for LinkExtractor and HtmlFiveParserLinkExtractor."""

import pytest

from scrapy_h5 import HtmlFiveResponse, HtmlFiveSelector
from scrapy_h5.extractor import HtmlFiveParserLinkExtractor, LinkExtractor


class TestCssLinkExtractor:
    """Tests for LinkExtractor class."""

    SAMPLE_HTML = b"""
    <html>
    <head><title>Test Page</title></head>
    <body>
        <div id="nav">
            <a href="/home">Home</a>
            <a href="/about">About</a>
            <a href="/contact">Contact</a>
        </div>
        <div id="content">
            <h1>Welcome</h1>
            <p>Check out our <a href="/products">products</a>.</p>
            <a href="http://external.com/page">External Link</a>
        </div>
        <div id="footer">
            <a href="/privacy">Privacy Policy</a>
            <area href="/sitemap" alt="Sitemap">
        </div>
    </body>
    </html>
    """

    def _create_response(self, backend: str, html: bytes | None = None) -> HtmlFiveResponse:
        """Create a HtmlFiveResponse for testing."""
        body = html if html is not None else self.SAMPLE_HTML
        return HtmlFiveResponse(url="http://example.com", body=body).with_backend(backend)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_all_links(self, backend: str) -> None:
        """Test extracting all links from HTML."""
        response = self._create_response(backend)
        extractor = LinkExtractor()
        links = extractor.extract_links(response)

        # Should find all <a> and <area> tags with href
        urls = [link.url for link in links]
        assert "/home" in urls or any("/home" in url for url in urls)
        assert "/about" in urls or any("/about" in url for url in urls)
        assert "/products" in urls or any("/products" in url for url in urls)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_with_allow_pattern(self, backend: str) -> None:
        """Test link extraction with allow regex pattern."""
        response = self._create_response(backend)
        extractor = LinkExtractor(allow=r"/products")
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        # Only /products should match
        assert len(urls) == 1
        assert "/products" in urls[0]

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_with_deny_pattern(self, backend: str) -> None:
        """Test link extraction with deny regex pattern."""
        response = self._create_response(backend)
        extractor = LinkExtractor(deny=r"/privacy")
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        # /privacy should be excluded
        assert not any("/privacy" in url for url in urls)
        # But other links should still be present
        assert len(urls) >= 1

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_with_allow_domains(self, backend: str) -> None:
        """Test link extraction with domain filtering."""
        html = b"""
        <html><body>
            <a href="http://allowed.com/page1">Allowed 1</a>
            <a href="http://allowed.com/page2">Allowed 2</a>
            <a href="http://blocked.com/page">Blocked</a>
        </body></html>
        """
        response = self._create_response(backend, html)
        extractor = LinkExtractor(allow_domains=["allowed.com"])
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert all("allowed.com" in url for url in urls)
        assert not any("blocked.com" in url for url in urls)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_with_deny_domains(self, backend: str) -> None:
        """Test link extraction with deny_domains."""
        html = b"""
        <html><body>
            <a href="http://good.com/page">Good</a>
            <a href="http://bad.com/page">Bad</a>
        </body></html>
        """
        response = self._create_response(backend, html)
        extractor = LinkExtractor(deny_domains=["bad.com"])
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert not any("bad.com" in url for url in urls)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_custom_tags(self, backend: str) -> None:
        """Test link extraction with custom tags."""
        html = b"""
        <html><body>
            <a href="/link-a">A Tag</a>
            <link href="/link-link" rel="stylesheet">
            <script src="/script.js"></script>
        </body></html>
        """
        response = self._create_response(backend, html)
        extractor = LinkExtractor(tags=["link"], attrs=["href"])
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert any("/link-link" in url for url in urls)
        # <a> should not be extracted since we only specified 'link'
        assert not any("/link-a" in url for url in urls)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_custom_attrs(self, backend: str) -> None:
        """Test link extraction with custom attributes."""
        html = b"""
        <html><body>
            <a href="/regular">Regular Link</a>
            <a data-url="/data-url">Data URL</a>
        </body></html>
        """
        response = self._create_response(backend, html)
        extractor = LinkExtractor(attrs=["data-url"])
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert any("/data-url" in url for url in urls)
        # href should not be extracted since we only specified 'data-url'
        assert not any("/regular" in url for url in urls)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_unique(self, backend: str) -> None:
        """Test unique link filtering."""
        html = b"""
        <html><body>
            <a href="/same">Link 1</a>
            <a href="/same">Link 2</a>
            <a href="/same">Link 3</a>
        </body></html>
        """
        response = self._create_response(backend, html)

        # With unique=True (default)
        extractor_unique = LinkExtractor(unique=True)
        links_unique = extractor_unique.extract_links(response)
        assert len(links_unique) == 1

        # With unique=False
        extractor_not_unique = LinkExtractor(unique=False)
        links_not_unique = extractor_not_unique.extract_links(response)
        assert len(links_not_unique) == 3  # noqa: PLR2004

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_strip_whitespace(self, backend: str) -> None:
        """Test whitespace stripping from URLs."""
        html = b"""
        <html><body>
            <a href="  /spaced  ">Spaced Link</a>
        </body></html>
        """
        response = self._create_response(backend, html)

        # With strip=True (default)
        extractor = LinkExtractor(strip=True)
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert len(urls) == 1
        # URL should be stripped
        assert "  " not in urls[0]

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_deny_extensions(self, backend: str) -> None:
        """Test denying specific file extensions."""
        html = b"""
        <html><body>
            <a href="/page.html">HTML Page</a>
            <a href="/image.jpg">Image</a>
            <a href="/doc.pdf">PDF</a>
        </body></html>
        """
        response = self._create_response(backend, html)
        extractor = LinkExtractor(deny_extensions=["jpg", "pdf"])
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert any("/page.html" in url for url in urls)
        assert not any(".jpg" in url for url in urls)
        assert not any(".pdf" in url for url in urls)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_empty_document(self, backend: str) -> None:
        """Test extracting links from empty document."""
        response = self._create_response(backend, b"<html><body></body></html>")
        extractor = LinkExtractor()
        links = extractor.extract_links(response)

        assert len(links) == 0

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_no_matching_tags(self, backend: str) -> None:
        """Test extraction when no tags match."""
        html = b"<html><body><div>No links here</div></body></html>"
        response = self._create_response(backend, html)
        extractor = LinkExtractor()
        links = extractor.extract_links(response)

        assert len(links) == 0

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_area_tag(self, backend: str) -> None:
        """Test that area tags are extracted by default."""
        html = b"""
        <html><body>
            <map name="imagemap">
                <area href="/area1" alt="Area 1">
                <area href="/area2" alt="Area 2">
            </map>
        </body></html>
        """
        response = self._create_response(backend, html)
        extractor = LinkExtractor()
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert any("/area1" in url for url in urls)
        assert any("/area2" in url for url in urls)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_process_value(self, backend: str) -> None:
        """Test custom process_value callback."""
        html = b"""
        <html><body>
            <a href="/page?track=123">Link</a>
        </body></html>
        """
        response = self._create_response(backend, html)

        def remove_tracking(url: str) -> str:
            """Remove tracking parameters from URL."""
            if "?" in url:
                return url.split("?")[0]
            return url

        extractor = LinkExtractor(process_value=remove_tracking)
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert len(urls) == 1
        assert "track=" not in urls[0]
        assert "/page" in urls[0]

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_extract_links_multiple_allow_patterns(self, backend: str) -> None:
        """Test multiple allow patterns."""
        html = b"""
        <html><body>
            <a href="/products/item1">Product 1</a>
            <a href="/services/service1">Service 1</a>
            <a href="/about">About</a>
        </body></html>
        """
        response = self._create_response(backend, html)
        extractor = LinkExtractor(allow=[r"/products", r"/services"])
        links = extractor.extract_links(response)

        urls = [link.url for link in links]
        assert len(urls) == 2  # noqa: PLR2004
        assert any("/products" in url for url in urls)
        assert any("/services" in url for url in urls)
        assert not any("/about" in url for url in urls)


class TestHtmlFiveParserLinkExtractor:
    """Tests for HtmlFiveParserLinkExtractor class."""

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_iter_links_basic(self, backend: str) -> None:
        """Test basic link iteration."""
        html = """
        <html><body>
            <a href="/link1">Link 1</a>
            <a href="/link2">Link 2</a>
        </body></html>
        """
        sel = HtmlFiveSelector(backend, text=html)
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a == "href",
        )

        links = list(extractor._iter_links(sel._root))  # noqa: SLF001
        assert len(links) == 2  # noqa: PLR2004

        # Each link should be (element, attr_name, attr_value)
        for _el, attr, value in links:
            assert attr == "href"
            assert value.startswith("/link")

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_iter_links_filters_tags(self, backend: str) -> None:
        """Test that tag filtering works."""
        html = """
        <html><body>
            <a href="/a-link">A Link</a>
            <area href="/area-link" alt="Area">
            <div href="/div-link">Div (should be ignored)</div>
        </body></html>
        """
        sel = HtmlFiveSelector(backend, text=html)
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a == "href",
        )

        links = list(extractor._iter_links(sel._root))  # noqa: SLF001
        values = [v for _, _, v in links]

        assert "/a-link" in values
        assert "/area-link" not in values
        assert "/div-link" not in values

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_iter_links_filters_attrs(self, backend: str) -> None:
        """Test that attribute filtering works."""
        html = """
        <html><body>
            <a href="/href-link">Href Link</a>
            <a data-link="/data-link">Data Link</a>
        </body></html>
        """
        sel = HtmlFiveSelector(backend, text=html)
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a == "data-link",
        )

        links = list(extractor._iter_links(sel._root))  # noqa: SLF001
        values = [v for _, _, v in links]

        assert "/data-link" in values
        assert "/href-link" not in values

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_iter_links_multiple_attrs(self, backend: str) -> None:
        """Test iteration with element having multiple matching attributes."""
        html = """
        <html><body>
            <a href="/href" data-link="/data">Multi Attr</a>
        </body></html>
        """
        sel = HtmlFiveSelector(backend, text=html)
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a in ("href", "data-link"),
        )

        links = list(extractor._iter_links(sel._root))  # noqa: SLF001
        values = [v for _, _, v in links]

        assert "/href" in values
        assert "/data" in values

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_iter_links_empty_document(self, backend: str) -> None:
        """Test iteration on empty document."""
        sel = HtmlFiveSelector(backend, text="<html><body></body></html>")
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a == "href",
        )

        links = list(extractor._iter_links(sel._root))  # noqa: SLF001
        assert len(links) == 0

    def test_iter_links_unsupported_type(self) -> None:
        """Test that unsupported document types raise TypeError."""
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a == "href",
        )

        with pytest.raises(TypeError, match="Unsupported document type"):
            list(extractor._iter_links("not a valid document"))  # noqa: SLF001

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_iter_links_nested_elements(self, backend: str) -> None:
        """Test iteration handles nested elements correctly."""
        html = """
        <html><body>
            <div>
                <nav>
                    <ul>
                        <li><a href="/link1">Link 1</a></li>
                        <li><a href="/link2">Link 2</a></li>
                    </ul>
                </nav>
            </div>
            <a href="/link3">Link 3</a>
        </body></html>
        """
        sel = HtmlFiveSelector(backend, text=html)
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a == "href",
        )

        links = list(extractor._iter_links(sel._root))  # noqa: SLF001
        values = [v for _, _, v in links]

        assert "/link1" in values
        assert "/link2" in values
        assert "/link3" in values
        assert len(links) == 3  # noqa: PLR2004

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_iter_links_with_empty_href(self, backend: str) -> None:
        """Test iteration handles empty href values."""
        html = """
        <html><body>
            <a href="">Empty Link</a>
            <a href="/valid">Valid Link</a>
        </body></html>
        """
        sel = HtmlFiveSelector(backend, text=html)
        extractor = HtmlFiveParserLinkExtractor(
            tag=lambda t: t == "a",
            attr=lambda a: a == "href",
        )

        links = list(extractor._iter_links(sel._root))  # noqa: SLF001
        values = [v for _, _, v in links]

        # Both should be yielded (filtering happens at higher level)
        assert "" in values
        assert "/valid" in values


class TestCssLinkExtractorInit:
    """Tests for LinkExtractor initialization."""

    def test_default_tags(self) -> None:
        """Test default tags are 'a' and 'area'."""
        extractor = LinkExtractor()
        # Check that the link_extractor has the right tag filter
        assert extractor.link_extractor.scan_tag("a")
        assert extractor.link_extractor.scan_tag("area")
        assert not extractor.link_extractor.scan_tag("div")

    def test_default_attrs(self) -> None:
        """Test default attrs is 'href'."""
        extractor = LinkExtractor()
        assert extractor.link_extractor.scan_attr("href")
        assert not extractor.link_extractor.scan_attr("src")

    def test_custom_tags(self) -> None:
        """Test custom tags parameter."""
        extractor = LinkExtractor(tags=["link", "script"])
        assert extractor.link_extractor.scan_tag("link")
        assert extractor.link_extractor.scan_tag("script")
        assert not extractor.link_extractor.scan_tag("a")

    def test_custom_attrs(self) -> None:
        """Test custom attrs parameter."""
        extractor = LinkExtractor(attrs=["src", "data-url"])
        assert extractor.link_extractor.scan_attr("src")
        assert extractor.link_extractor.scan_attr("data-url")
        assert not extractor.link_extractor.scan_attr("href")

    def test_link_extractor_type(self) -> None:
        """Test that link_extractor is HtmlFiveParserLinkExtractor."""
        extractor = LinkExtractor()
        assert isinstance(extractor.link_extractor, HtmlFiveParserLinkExtractor)
