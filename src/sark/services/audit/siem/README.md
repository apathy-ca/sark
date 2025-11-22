# SIEM Integration Framework

This directory contains the SIEM (Security Information and Event Management) integration framework for SARK.

## Files

- **`__init__.py`** - Package exports
- **`base.py`** - Abstract BaseSIEM class and core interfaces
- **`retry_handler.py`** - Retry logic with exponential backoff
- **`batch_handler.py`** - Event batching and aggregation
- **`metrics.py`** - Prometheus metrics for monitoring

## Quick Start

```python
from sark.services.audit.siem import (
    BaseSIEM,
    SIEMConfig,
    RetryHandler,
    RetryConfig,
    BatchHandler,
    BatchConfig,
)

# Create a SIEM implementation
class MySIEM(BaseSIEM):
    async def send_event(self, event):
        # Implementation
        pass

    async def send_batch(self, events):
        # Implementation
        pass

    async def health_check(self):
        # Implementation
        pass

    def format_event(self, event):
        # Implementation
        pass

# Configure and use
config = SIEMConfig(batch_size=100)
siem = MySIEM(config)

# Use with batch handler
batch_handler = BatchHandler(siem.send_batch)
await batch_handler.start()
await batch_handler.enqueue(event)
await batch_handler.stop(flush=True)
```

## Documentation

See `/docs/siem/SIEM_FRAMEWORK.md` for comprehensive documentation.

## Tests

Tests are located in `/tests/test_audit/`:
- `test_siem_base.py` - BaseSIEM tests
- `test_retry_handler.py` - RetryHandler tests
- `test_batch_handler.py` - BatchHandler tests

Run tests:
```bash
pytest tests/test_audit/ -v
```

## Coverage

Current test coverage:
- base.py: 100%
- retry_handler.py: 90.48%
- batch_handler.py: 90.32%

All modules exceed the 85% coverage target.
