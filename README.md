# Parsel H5

Scrapy integration for the `html5ever` and `lexbor` HTML parsers.

This package provides a Scrapy Downloader Middleware that replaces the default `lxml`-based HTML parsing with a HTML5
one.

## Why html5ever?

- **Better HTML5 compliance**: Parses HTML the way browsers do
- **Handles malformed HTML gracefully**: More forgiving with real-world HTML
- **As fast as Parsel**: Rust-based parser with Python bindings (`markupever`)

## Why Lexbor?

- **Fastest HTML5 parser**: C-based parser with Python bindings (`selectolax`)
- **Better HTML5 compliance**: Parses HTML the way browsers do
- **Handles malformed HTML gracefully**: More forgiving with real-world HTML

## Installation

```bash
pip install scrapy-h5
```

Or with uv:

```bash
uv add scrapy-h5
```

## Quick start

### 1. Enable the middleware in your Scrapy project

Add to your `settings.py`:

```python
DOWNLOADER_MIDDLEWARES = {
    'scrapy_h5.HtmlFiveResponseMiddleware': 950,
}

# Optional: disable globally (backend by default)
# HTML5_BACKEND = False
```

### 2. Use in your spider

```python
import scrapy


class MySpider(scrapy.Spider):
    name = 'myspider'
    start_urls = ['https://example.com']

    def parse(self, response):
        # CSS selectors work as expected
        titles = response.css('h1::text').getall()

        # Attribute extraction
        links = response.css('a::attr(href)').getall()

        # Chained selectors
        for item in response.css('div.product'):
            yield {
                'name': item.css('h2::text').get(),
                'price': item.css('.price::text').get(),
                'url': item.css('a::attr(href)').get(),
            }
```

## XPath and JMESPath support

XPath and JMESPath selectors are not supported. Use CSS selectors instead.

## Per-request control

You can change/disable html5 backend per request using `meta`:

```python
def start_requests(self):
    # HTML5 parsing backend (default)
    yield scrapy.Request(url, callback=self.parse)

    # Disable html5 for this request (use lxml instead)
    yield scrapy.Request(
        url2,
        callback=self.parse_legacy,
        meta={'use_html5': False}
    )


def parse_with_html5(self, response):
    # Force html5 even if HTML5_BACKEND=False
    yield scrapy.Request(
        url,
        callback=self.parse,
        meta={'use_html5': 'html5ever'}
    )
```

## API reference

### Classes

- **`HtmlFiveSelector`**: Selector class wrapping `html5ever` and `lexbor` elements
- **`HtmlFiveSelectorList`**: List of selectors with bulk operations
- **`HtmlFiveResponse`**: Response class with html5-based selector
- **`HtmlFiveResponseMiddleware`**: Scrapy Downloader Middleware that replaces `HtmlResponse` with `HtmlFiveResponse`

### Exceptions

- **`XPathConversionError`**: Raised when an XPath expression cannot be converted to CSS
- **`HtmlFiveParseError`**: Raised when HTML parsing fails
- **`HtmlFiveSelectorError`**: Base exception for selector errors
- **`HtmlFiveSelectError`**: Raised when CSS selection fails

### Settings

| Setting         | Default  | Description                                                              |
|-----------------|----------|--------------------------------------------------------------------------|
| `HTML5_BACKEND` | `lexbor` | Global html5 backend. `lexbor` and `html5ever` enables, `False` disables |

### Request meta

| Key         | Type   | Description                                                              |
|-------------|--------|--------------------------------------------------------------------------|
| `use_html5` | `bool` | Per-request override. `lexbor` and `html5ever` enables, `False` disables |

## Middleware priority

The default priority (950) is chosen to run:

- After `HttpCompressionMiddleware` (590) - responses are decompressed
- After `HttpCacheMiddleware` (900) - cached responses are handled
- Before most other processing

Adjust the priority if needed:

```python
DOWNLOADER_MIDDLEWARES = {
    'scrapy_h5.HtmlFiveResponseMiddleware': 400,  # Earlier in the chain
}
```

## License

MIT
