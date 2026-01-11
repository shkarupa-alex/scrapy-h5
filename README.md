# Parsel H5

Scrapy integration for the `html5ever` HTML parser.

This package provides a Scrapy Downloader Middleware that replaces the default `lxml`-based HTML parsing with
`html5ever`, a browser-grade HTML5 parser written in Rust.

## Why html5ever?

- **Better HTML5 compliance**: Parses HTML the way browsers do
- **Handles malformed HTML gracefully**: More forgiving with real-world HTML
- **Fast**: Rust-based parser with Python bindings (`markupever`)

## Installation

```bash
pip install parsel-h5
```

Or with uv:

```bash
uv add parsel-h5
```

## Quick Start

### 1. Enable the middleware in your Scrapy project

Add to your `settings.py`:

```python
DOWNLOADER_MIDDLEWARES = {
    'parsel_h5.HtmlFiveResponseMiddleware': 950,
}

# Optional: disable globally (enabled by default)
# HTML5_ENABLED = False
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

## XPath Support

Common XPath patterns are automatically converted to CSS selectors:

```python
# These XPath patterns work:
response.xpath('//div')  # -> CSS: div
response.xpath('//div/p')  # -> CSS: div > p (child)
response.xpath('//div//p')  # -> CSS: div p (descendant)
response.xpath('//*[@id="main"]')  # -> CSS: #main
response.xpath('//*[@class="x"]')  # -> CSS: .x
response.xpath('//a/@href')  # -> CSS: a (extracts href)
response.xpath('//p/text()')  # -> CSS: p (extracts text)
```

**Note**: Complex XPath expressions (predicates, axes like `following-sibling::`, functions like `contains()`) are not
supported and will raise `XPathConversionError`. Use CSS selectors instead.

## Per-Request Control

You can enable/disable html5ever parsing per request using `meta`:

```python
def start_requests(self):
    # HTML5 parsing enabled (default)
    yield scrapy.Request(url, callback=self.parse)

    # Disable html5ever for this request (use lxml instead)
    yield scrapy.Request(
        url2,
        callback=self.parse_legacy,
        meta={'use_html5': False}
    )


def parse_with_html5(self, response):
    # Force html5ever even if HTML5_ENABLED=False
    yield scrapy.Request(
        url,
        callback=self.parse,
        meta={'use_html5': True}
    )
```

## API Reference

### Classes

- **`HtmlFiveSelector`**: Selector class wrapping `html5ever` elements
- **`HtmlFiveSelectorList`**: List of selectors with bulk operations
- **`HtmlFiveResponse`**: Response class with html5ever-based selector
- **`HtmlFiveResponseMiddleware`**: Scrapy Downloader Middleware that replaces `HtmlResponse` with `HtmlFiveResponse`

### Exceptions

- **`XPathConversionError`**: Raised when an XPath expression cannot be converted to CSS
- **`HtmlFiveParseError`**: Raised when HTML parsing fails
- **`HtmlFiveSelectorError`**: Base exception for selector errors
- **`HtmlFiveSelectError`**: Raised when CSS selection fails

### Settings

| Setting         | Default | Description                                 |
|-----------------|---------|---------------------------------------------|
| `HTML5_ENABLED` | `True`  | Global enable/disable for html5ever parsing |

### Request Meta

| Key         | Type   | Description                                            |
|-------------|--------|--------------------------------------------------------|
| `use_html5` | `bool` | Per-request override. `True` enables, `False` disables |

## Limitations

1. **XPath**: Only common patterns are supported. Complex expressions need to use CSS selectors.
2. **Namespaces**: XML namespace support is not available. `remove_namespaces()` is a no-op.
3. **JMESPath**: JSON selectors pass through to the original parsel implementation.

## Middleware Priority

The default priority (950) is chosen to run:

- After `HttpCompressionMiddleware` (590) - responses are decompressed
- After `HttpCacheMiddleware` (900) - cached responses are handled
- Before most other processing

Adjust the priority if needed:

```python
DOWNLOADER_MIDDLEWARES = {
    'parsel_h5.HtmlFiveResponseMiddleware': 400,  # Earlier in the chain
}
```

## License

MIT
