"""Tests for HtmlFiveResponseMiddleware."""

from unittest.mock import MagicMock

from scrapy import Request, Spider
from scrapy.http import HtmlResponse, JsonResponse, TextResponse, XmlResponse

from parsel_h5 import HtmlFiveResponse, HtmlFiveResponseMiddleware


class TestHtmlFiveResponseMiddleware:
    """Tests for HtmlFiveResponseMiddleware class."""

    def create_middleware(self, enabled: bool = True) -> HtmlFiveResponseMiddleware:
        """Create a middleware instance."""
        return HtmlFiveResponseMiddleware(enabled=enabled)

    def create_request(self, url: str = "http://example.com", **meta: object) -> Request:
        """Create a test request."""
        return Request(url=url, meta=meta)

    def create_html_response(
        self,
        url: str = "http://example.com",
        body: bytes = b"<html><body>Test</body></html>",
    ) -> HtmlResponse:
        """Create a test HTML response."""
        return HtmlResponse(url=url, body=body)

    def test_process_html_response_enabled(self) -> None:
        """Test that HTML responses are replaced when enabled."""
        middleware = self.create_middleware(enabled=True)
        request = self.create_request()
        response = self.create_html_response()
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        assert isinstance(result, HtmlFiveResponse)
        assert result.url == response.url
        assert result.body == response.body

    def test_process_html_response_disabled(self) -> None:
        """Test that HTML responses are not replaced when disabled."""
        middleware = self.create_middleware(enabled=False)
        request = self.create_request()
        response = self.create_html_response()
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        assert isinstance(result, HtmlResponse)
        assert not isinstance(result, HtmlFiveResponse)

    def test_process_response_meta_disable(self) -> None:
        """Test per-request disable via meta."""
        middleware = self.create_middleware(enabled=True)
        request = self.create_request(use_html5=False)
        response = self.create_html_response()
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        assert isinstance(result, HtmlResponse)
        assert not isinstance(result, HtmlFiveResponse)

    def test_process_response_meta_enable_override(self) -> None:
        """Test per-request enable overrides global disable."""
        middleware = self.create_middleware(enabled=False)
        request = self.create_request(use_html5=True)
        response = self.create_html_response()
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        assert isinstance(result, HtmlFiveResponse)

    def test_xml_response_passthrough(self) -> None:
        """Test that XML responses pass through unchanged."""
        middleware = self.create_middleware(enabled=True)
        request = self.create_request()
        response = XmlResponse(url="http://example.com", body=b"<root/>")
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        assert isinstance(result, XmlResponse)
        assert result is response

    def test_json_response_passthrough(self) -> None:
        """Test that JSON responses pass through unchanged."""
        middleware = self.create_middleware(enabled=True)
        request = self.create_request()
        response = JsonResponse(url="http://example.com", body=b'{"key": "value"}')
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        assert isinstance(result, JsonResponse)
        assert result is response

    def test_text_response_passthrough(self) -> None:
        """Test that plain text responses pass through unchanged."""
        middleware = self.create_middleware(enabled=True)
        request = self.create_request()
        response = TextResponse(url="http://example.com", body=b"plain text")
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        # TextResponse is not HtmlResponse, so passes through
        assert isinstance(result, TextResponse)
        assert not isinstance(result, HtmlResponse)

    def test_already_h5_response_passthrough(self) -> None:
        """Test that HtmlFiveResponse passes through unchanged."""
        middleware = self.create_middleware(enabled=True)
        request = self.create_request()
        response = HtmlFiveResponse(url="http://example.com", body=b"<html>test</html>")
        spider = MagicMock(spec=Spider)

        result = middleware.process_response(request, response, spider)

        assert result is response

    def test_from_crawler(self) -> None:
        """Test from_crawler class method."""
        crawler = MagicMock()
        crawler.settings.getbool.return_value = True
        crawler.signals = MagicMock()

        middleware = HtmlFiveResponseMiddleware.from_crawler(crawler)

        assert middleware.enabled is True
        crawler.settings.getbool.assert_called_once_with("HTML5_ENABLED", default=True)

    def test_from_crawler_disabled(self) -> None:
        """Test from_crawler with HTML5_ENABLED=False."""
        crawler = MagicMock()
        crawler.settings.getbool.return_value = False
        crawler.signals = MagicMock()

        middleware = HtmlFiveResponseMiddleware.from_crawler(crawler)

        assert middleware.enabled is False

    def test_spider_opened_logging(self) -> None:
        """Test spider_opened logs correctly."""
        middleware = self.create_middleware(enabled=True)
        spider = MagicMock(spec=Spider)

        # Should not raise
        middleware.spider_opened(spider)

        spider.logger.debug.assert_called_once()
        call_args = spider.logger.debug.call_args
        assert "HtmlFiveResponseMiddleware" in call_args[0][0]
        assert call_args[0][1] is True


class TestHtmlFiveResponse:
    """Tests for HtmlFiveResponse class."""

    SAMPLE_HTML = b"""
    <html>
    <body>
        <h1>Title</h1>
        <p class="content">Paragraph</p>
        <a href="/link">Link</a>
    </body>
    </html>
    """

    def test_selector_property(self) -> None:
        """Test selector property returns HtmlFiveSelector."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML)
        from parsel_h5 import HtmlFiveSelector

        assert isinstance(response.selector, HtmlFiveSelector)

    def test_selector_cached(self) -> None:
        """Test selector is cached."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML)
        selector1 = response.selector
        selector2 = response.selector
        assert selector1 is selector2

    def test_css_method(self) -> None:
        """Test css() method."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML)
        result = response.css("h1::text").get()
        assert result == "Title"

    def test_xpath_method(self) -> None:
        """Test xpath() method."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML)
        result = response.xpath("//a/@href").get()
        assert result == "/link"

    def test_css_getall(self) -> None:
        """Test css().getall()."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML)
        result = response.css("h1::text, p::text").getall()
        # Note: CSS selector order may vary
        assert "Title" in result

    def test_complex_selectors(self) -> None:
        """Test complex CSS selectors work."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML)
        result = response.css("p.content::text").get()
        assert result == "Paragraph"
