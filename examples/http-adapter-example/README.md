# HTTP Adapter Example

This example demonstrates how to use the HTTP Adapter to integrate REST APIs with SARK v2.0.

## Overview

The HTTP Adapter enables SARK to govern REST APIs through:
- **OpenAPI Discovery**: Automatically discover capabilities from OpenAPI/Swagger specs
- **Authentication**: Support for Basic, Bearer, OAuth2, and API Key authentication
- **Rate Limiting**: Prevent overwhelming APIs with built-in rate limiting
- **Circuit Breaker**: Fail-fast when APIs are unhealthy
- **Retry Logic**: Automatic retries with exponential backoff

## Prerequisites

```bash
pip install httpx pyyaml
```

## Examples

### 1. Basic REST API Integration

See `basic_example.py` for a simple example using a public API.

```bash
python basic_example.py
```

### 2. OpenAPI Discovery

See `openapi_discovery.py` for automatic capability discovery.

```bash
python openapi_discovery.py
```

### 3. Authentication Examples

See `auth_examples.py` for different authentication strategies.

```bash
python auth_examples.py
```

### 4. Advanced Features

See `advanced_example.py` for rate limiting and circuit breaker usage.

```bash
python advanced_example.py
```

## File Structure

```
http-adapter-example/
├── README.md                  # This file
├── basic_example.py          # Basic usage
├── openapi_discovery.py      # OpenAPI discovery
├── auth_examples.py          # Authentication strategies
├── advanced_example.py       # Rate limiting and circuit breaker
└── test_api_spec.json        # Sample OpenAPI spec for testing
```

## Configuration

### No Authentication

```python
from sark.adapters.http import HTTPAdapter

adapter = HTTPAdapter(
    base_url="https://api.example.com",
    auth_config={"type": "none"}
)
```

### API Key Authentication

```python
adapter = HTTPAdapter(
    base_url="https://api.example.com",
    auth_config={
        "type": "api_key",
        "api_key": "your-api-key-here",
        "location": "header",
        "key_name": "X-API-Key"
    }
)
```

### OAuth2

```python
adapter = HTTPAdapter(
    base_url="https://api.example.com",
    auth_config={
        "type": "oauth2",
        "token_url": "https://auth.example.com/token",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "grant_type": "client_credentials"
    }
)
```

### Rate Limiting

```python
adapter = HTTPAdapter(
    base_url="https://api.example.com",
    rate_limit=10.0,  # 10 requests per second
)
```

### Circuit Breaker

```python
adapter = HTTPAdapter(
    base_url="https://api.example.com",
    circuit_breaker_threshold=5,  # Open circuit after 5 failures
)
```

## Integration with SARK

Once configured, the HTTP adapter integrates seamlessly with SARK's governance:

```python
from sark.adapters import get_registry

# Register the adapter
registry = get_registry()
registry.register_adapter("http", adapter)

# Discover resources
resources = await adapter.discover_resources({
    "base_url": "https://api.example.com",
    "openapi_spec_url": "https://api.example.com/openapi.json"
})

# Get capabilities
capabilities = await adapter.get_capabilities(resources[0])

# Invoke capability with governance
from sark.models.base import InvocationRequest

request = InvocationRequest(
    capability_id=capabilities[0].id,
    principal_id="user@example.com",
    arguments={"param": "value"}
)

result = await adapter.invoke(request)
```

## Testing

Run the test suite:

```bash
pytest tests/adapters/test_http_adapter.py -v
```

## Next Steps

- Explore the source code in `src/sark/adapters/http/`
- Read the [HTTP Adapter documentation](../../docs/v2.0/adapters/http-adapter.md)
- Try integrating your own REST APIs

## Support

For questions and issues, see the main SARK documentation.
