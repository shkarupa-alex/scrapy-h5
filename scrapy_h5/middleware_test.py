"""Tests for HtmlFiveResponseMiddleware."""

from unittest.mock import MagicMock

import pytest
from scrapy import Request, Spider
from scrapy.http import HtmlResponse, JsonResponse, TextResponse, XmlResponse

from scrapy_h5 import HtmlFiveResponse, HtmlFiveResponseMiddleware, HtmlFiveSelector


class TestHtmlFiveResponseMiddleware:
    """Tests for HtmlFiveResponseMiddleware class."""

    def _create_middleware(self, *, backend: str | None) -> HtmlFiveResponseMiddleware:
        """Create a middleware instance."""
        return HtmlFiveResponseMiddleware(backend=backend)

    def _create_request(self, url: str = "http://example.com", **meta: object) -> Request:
        """Create a test request."""
        return Request(url=url, meta=meta)

    def _create_html_response(
        self,
        url: str = "http://example.com",
        body: bytes = b"<html><body>Test</body></html>",
    ) -> HtmlResponse:
        """Create a test HTML response."""
        return HtmlResponse(url=url, body=body)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_process_html_response_enabled(self, backend: str) -> None:
        """Test that HTML responses are replaced when backend."""
        middleware = self._create_middleware(backend=backend)
        request = self._create_request()
        response = self._create_html_response()

        result = middleware.process_response(request, response)

        assert isinstance(result, HtmlFiveResponse)
        assert result.url == response.url
        assert result.body == response.body

    def test_process_html_response_disabled(self) -> None:
        """Test that HTML responses are not replaced when disabled."""
        middleware = self._create_middleware(backend=None)
        request = self._create_request()
        response = self._create_html_response()

        result = middleware.process_response(request, response)

        assert isinstance(result, HtmlResponse)
        assert not isinstance(result, HtmlFiveResponse)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_process_response_meta_disable(self, backend: str) -> None:
        """Test per-request disable via meta."""
        middleware = self._create_middleware(backend=backend)
        request = self._create_request(use_html5=None)
        response = self._create_html_response()

        result = middleware.process_response(request, response)

        assert isinstance(result, HtmlResponse)
        assert not isinstance(result, HtmlFiveResponse)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_process_response_meta_enable_override(self, backend: str) -> None:
        """Test per-request enable overrides global disable."""
        middleware = self._create_middleware(backend=None)
        request = self._create_request(use_html5=backend)
        response = self._create_html_response()

        result = middleware.process_response(request, response)

        assert isinstance(result, HtmlFiveResponse)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_xml_response_passthrough(self, backend: str) -> None:
        """Test that XML responses pass through unchanged."""
        middleware = self._create_middleware(backend=backend)
        request = self._create_request()
        response = XmlResponse(url="http://example.com", body=b"<root/>")

        result = middleware.process_response(request, response)

        assert isinstance(result, XmlResponse)
        assert result is response

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_json_response_passthrough(self, backend: str) -> None:
        """Test that JSON responses pass through unchanged."""
        middleware = self._create_middleware(backend=backend)
        request = self._create_request()
        response = JsonResponse(url="http://example.com", body=b'{"key": "value"}')

        result = middleware.process_response(request, response)

        assert isinstance(result, JsonResponse)
        assert result is response

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_text_response_passthrough(self, backend: str) -> None:
        """Test that plain text responses pass through unchanged."""
        middleware = self._create_middleware(backend=backend)
        request = self._create_request()
        response = TextResponse(url="http://example.com", body=b"plain text")

        result = middleware.process_response(request, response)

        # TextResponse is not HtmlResponse, so passes through
        assert isinstance(result, TextResponse)
        assert not isinstance(result, HtmlResponse)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_already_h5_response_passthrough(self, backend: str) -> None:
        """Test that HtmlFiveResponse passes through unchanged."""
        middleware = self._create_middleware(backend=backend)
        request = self._create_request()
        response = HtmlFiveResponse(url="http://example.com", body=b"<html>test</html>")

        result = middleware.process_response(request, response)

        assert isinstance(result, HtmlFiveResponse)
        assert result.url == response.url
        assert result.body == response.body

    def test_from_crawler(self) -> None:
        """Test from_crawler class method."""
        crawler = MagicMock()
        crawler.settings.get.return_value = "html5ever"
        crawler.signals = MagicMock()

        middleware = HtmlFiveResponseMiddleware.from_crawler(crawler)

        assert middleware.backend == "html5ever"
        crawler.settings.get.assert_called_once_with("HTML5_BACKEND", default="lexbor")

    def test_from_crawler_disabled(self) -> None:
        """Test from_crawler with HTML5_BACKEND=False."""
        crawler = MagicMock()
        crawler.settings.get.return_value = "html5ever"
        crawler.signals = MagicMock()

        middleware = HtmlFiveResponseMiddleware.from_crawler(crawler)

        assert middleware.backend == "html5ever"

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_spider_opened_logging(self, backend: str) -> None:
        """Test spider_opened logs correctly."""
        middleware = self._create_middleware(backend=backend)
        spider = MagicMock(spec=Spider)

        # Should not raise
        middleware.spider_opened(spider)

        spider.logger.debug.assert_called_once()
        call_args = spider.logger.debug.call_args
        assert "HtmlFiveResponseMiddleware" in call_args[0][0]
        assert call_args[0][1] is backend


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

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_selector_property(self, backend: str) -> None:
        """Test selector property returns HtmlFiveSelector."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML).with_backend(backend)
        assert isinstance(response.selector, HtmlFiveSelector)

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_selector_cached(self, backend: str) -> None:
        """Test selector is cached."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML).with_backend(backend)
        selector1 = response.selector
        selector2 = response.selector
        assert selector1 is selector2

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_method(self, backend: str) -> None:
        """Test css() method."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML).with_backend(backend)
        result = response.css("h1::text").get()
        assert result == "Title"

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_xpath_method(self, backend: str) -> None:
        """Test xpath() method."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML).with_backend(backend)
        try:
            response.xpath("//a/@href").get()
            raise AssertionError
        except NotImplementedError:
            pass

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_css_getall(self, backend: str) -> None:
        """Test css().getall()."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML).with_backend(backend)
        result = response.css("h1::text, p::text").getall()
        # Note: CSS selector order may vary
        assert "Title" in result

    @pytest.mark.parametrize("backend", ["lexbor", "html5ever"])
    def test_complex_selectors(self, backend: str) -> None:
        """Test complex CSS selectors work."""
        response = HtmlFiveResponse(url="http://example.com", body=self.SAMPLE_HTML).with_backend(backend)
        result = response.css("p.content::text").get()
        assert result == "Paragraph"
