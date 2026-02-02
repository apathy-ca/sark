# Home Analytics Module

The analytics module provides home users with comprehensive visibility into LLM usage patterns, costs, and statistics. It uses SQLite for lightweight storage optimized for home deployments.

## Overview

The analytics system tracks:
- **Token Usage**: Per-device, per-endpoint, per-day token consumption
- **Cost Estimates**: Calculated costs based on configurable provider rates
- **Usage Trends**: Daily/weekly/monthly patterns and anomaly detection
- **Reports**: Exportable usage reports in JSON and CSV formats

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Analytics Service                         │
│  (Unified interface for dashboard and recording)            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Token        │  │ Cost         │  │ Trend        │       │
│  │ Tracker      │  │ Calculator   │  │ Analyzer     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │            Usage Reporter                         │       │
│  │  (Reports, CSV/JSON export)                      │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    SQLite Storage                            │
│  usage_events | daily_aggregates | provider_pricing         │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Recording Usage

```python
from sark.services.analytics import AnalyticsService

async def record_llm_request(db: AsyncSession):
    analytics = AnalyticsService(db)

    event = await analytics.record_usage(
        device_ip="192.168.1.100",
        endpoint="openai/chat/completions",
        provider="openai",
        model="gpt-4",
        tokens_prompt=150,
        tokens_response=200,
        device_name="Living Room Mac",
    )
    # Cost is automatically calculated based on provider rates
```

### Getting Dashboard Stats

```python
stats = await analytics.get_dashboard_stats()

# Returns:
# {
#   "today": {"requests": 50, "tokens": 15000, "cost_estimate": 0.45},
#   "week": {"requests": 350, "tokens": 105000, "cost_estimate": 3.15},
#   "month": {"requests": 1200, "tokens": 360000, "cost_estimate": 10.80},
#   "top_devices": [...],
#   "top_endpoints": [...],
#   "peak_hours": [10, 14, 20],
#   "recent_activity": [...]
# }
```

### Generating Reports

```python
from sark.services.analytics import ReportPeriod

# Generate weekly report
report = await analytics.generate_report(period=ReportPeriod.WEEK)

# Export as CSV
csv_content = await analytics.export_report_csv(
    period=ReportPeriod.MONTH,
    include_details=True,  # Include individual events
)
```

## API Endpoints

### Dashboard

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/dashboard` | GET | Full dashboard statistics |
| `/api/analytics/summary` | GET | Quick summary (today/week/month) |

### Usage Recording

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/usage` | POST | Record a usage event |
| `/api/analytics/usage/daily` | GET | Daily usage for a device |
| `/api/analytics/usage/device/{ip}` | GET | Device usage summary |
| `/api/analytics/usage/devices` | GET | Top devices by usage |

### Trend Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/trends/usage` | GET | Token usage trend |
| `/api/analytics/trends/cost` | GET | Cost trend |
| `/api/analytics/trends/peak-hours` | GET | Peak usage hours |
| `/api/analytics/trends/weekdays` | GET | Weekday patterns |
| `/api/analytics/trends/anomalies` | GET | Anomaly detection |
| `/api/analytics/trends/compare` | GET | Period comparison |

### Reports

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/reports` | GET | Generate JSON report |
| `/api/analytics/reports/export/csv` | GET | Download CSV report |
| `/api/analytics/reports/export/json` | GET | Download JSON report |

### Cost Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/cost/estimate` | POST | Estimate cost for tokens |
| `/api/analytics/cost/rates` | GET | List provider rates |
| `/api/analytics/cost/rates` | POST | Update provider rate (admin) |

### Maintenance

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/maintenance/cleanup` | POST | Clean old data (admin) |
| `/api/analytics/maintenance/aggregate` | POST | Update daily aggregates (admin) |

## Services Reference

### TokenTrackerService

Tracks token usage per device and endpoint.

```python
from sark.services.analytics import TokenTrackerService

tracker = TokenTrackerService(db)

# Record usage
await tracker.record(
    device_ip="192.168.1.100",
    endpoint="openai/chat",
    provider="openai",
    tokens_prompt=100,
    tokens_response=50,
    model="gpt-4",
)

# Get daily stats
daily = await tracker.get_daily("192.168.1.100")
# {"total": 5000, "prompt": 3000, "response": 2000, "by_endpoint": {...}}

# Get top devices
top = await tracker.get_top_devices(days=7, limit=10)
```

### CostCalculatorService

Calculates costs based on configurable provider rates.

```python
from sark.services.analytics import CostCalculatorService

calculator = CostCalculatorService(db)

# Estimate cost
estimate = await calculator.estimate(
    tokens_prompt=1000,
    tokens_response=500,
    provider="openai",
    model="gpt-4",
)
# {"cost_usd": 0.06, "breakdown": {...}, "rate": {...}}

# Get all rates
rates = await calculator.get_rates(provider="openai")

# Set custom rate
await calculator.set_rate(
    provider="custom",
    model="my-model",
    prompt_per_1m=Decimal("5.00"),
    response_per_1m=Decimal("10.00"),
)
```

### TrendAnalyzerService

Analyzes usage patterns and trends.

```python
from sark.services.analytics import TrendAnalyzerService, TrendMetric

analyzer = TrendAnalyzerService(db)

# Analyze token trend
trend = await analyzer.analyze_trend(
    metric=TrendMetric.TOKENS,
    days=30,
)
# {"trend_direction": "up", "change_percent": 15.0, "data_points": [...]}

# Get peak hours
peaks = await analyzer.get_peak_hours(days=7)
# {"peak_hours_by_requests": [10, 14], "hourly_data": [...]}

# Detect anomalies
anomalies = await analyzer.detect_anomalies(days=30, threshold_std=2.0)
```

### UsageReporterService

Generates comprehensive usage reports.

```python
from sark.services.analytics import UsageReporterService, ReportPeriod

reporter = UsageReporterService(db)

# Generate report
report = await reporter.generate(
    period=ReportPeriod.WEEK,
    device_ip="192.168.1.100",  # Optional filter
)

# Export CSV
csv = await reporter.export_csv(period=ReportPeriod.MONTH)

# Quick summary
summary = await reporter.get_quick_summary()
```

## Data Models

### UsageEvent

Stores individual LLM request records.

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| timestamp | DATETIME | Event timestamp |
| device_ip | VARCHAR(45) | Device IP address |
| device_name | VARCHAR(255) | Human-readable device name |
| endpoint | VARCHAR(100) | API endpoint called |
| provider | VARCHAR(50) | LLM provider (openai, anthropic, etc.) |
| model | VARCHAR(100) | Model name |
| tokens_prompt | INTEGER | Prompt token count |
| tokens_response | INTEGER | Response token count |
| cost_estimate | DECIMAL | Estimated cost in USD |
| request_id | VARCHAR(36) | Request correlation ID |
| metadata | JSON | Additional metadata |

### DailyAggregate

Pre-computed daily summaries for fast queries.

| Field | Type | Description |
|-------|------|-------------|
| date | VARCHAR(10) | Date (YYYY-MM-DD) |
| device_ip | VARCHAR(45) | Device IP |
| endpoint | VARCHAR(100) | Endpoint |
| provider | VARCHAR(50) | Provider |
| request_count | INTEGER | Number of requests |
| tokens_prompt_total | INTEGER | Total prompt tokens |
| tokens_response_total | INTEGER | Total response tokens |
| cost_total | DECIMAL | Total cost |

### ProviderPricing

Configurable pricing rates.

| Field | Type | Description |
|-------|------|-------------|
| provider | VARCHAR(50) | Provider name |
| model | VARCHAR(100) | Model name |
| prompt_per_1m | DECIMAL | Cost per 1M prompt tokens |
| response_per_1m | DECIMAL | Cost per 1M response tokens |
| currency | VARCHAR(3) | Currency code |
| effective_date | DATETIME | Rate effective date |
| notes | TEXT | Optional notes |

## Default Provider Rates

The following rates are included by default (as of January 2025):

### OpenAI
- gpt-4-turbo: $10.00 / $30.00 per 1M tokens
- gpt-4: $30.00 / $60.00 per 1M tokens
- gpt-4o: $2.50 / $10.00 per 1M tokens
- gpt-4o-mini: $0.15 / $0.60 per 1M tokens
- gpt-3.5-turbo: $0.50 / $1.50 per 1M tokens

### Anthropic
- claude-3-opus: $15.00 / $75.00 per 1M tokens
- claude-3-sonnet: $3.00 / $15.00 per 1M tokens
- claude-3.5-sonnet: $3.00 / $15.00 per 1M tokens
- claude-3-haiku: $0.25 / $1.25 per 1M tokens

### Google
- gemini-1.5-pro: $1.25 / $5.00 per 1M tokens
- gemini-1.5-flash: $0.075 / $0.30 per 1M tokens
- gemini-2.0-flash: $0.10 / $0.40 per 1M tokens

### Mistral
- mistral-large: $2.00 / $6.00 per 1M tokens
- mistral-small: $0.20 / $0.60 per 1M tokens

## Performance Considerations

### SQLite Optimization

The module uses several optimizations for home deployments:

1. **WAL Mode**: Enables concurrent reads during writes
2. **Indexes**: Composite indexes on common query patterns
3. **Pre-aggregation**: Daily aggregates reduce dashboard query time
4. **Data Retention**: Automatic cleanup of old data (default: 1 year)

### Recommended Settings

```python
# Enable WAL mode on connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(conn, record):
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
    cursor.close()
```

### Storage Estimates

For a typical home with 1000 requests/day:
- Raw events: ~100KB/day, ~36MB/year
- With aggregates: ~150KB/day, ~55MB/year
- With 1-year retention: Under 100MB total

## Best Practices

1. **Record All Requests**: Call `record_usage()` for every LLM request to ensure accurate tracking

2. **Use Device Names**: Set `device_name` to make reports more readable

3. **Run Daily Aggregation**: Schedule daily aggregate updates for faster dashboard queries

4. **Configure Retention**: Set appropriate retention period based on storage constraints

5. **Update Pricing**: Update provider rates when prices change to maintain accurate cost estimates

## Example: Integration with Gateway

```python
# In your gateway middleware
async def track_request(request, response):
    # Extract token counts from response
    usage = response.get("usage", {})

    await analytics.record_usage(
        device_ip=request.client.host,
        endpoint=request.url.path,
        provider=extract_provider(request),
        model=response.get("model"),
        tokens_prompt=usage.get("prompt_tokens", 0),
        tokens_response=usage.get("completion_tokens", 0),
        request_id=str(request.state.request_id),
    )
```

## Troubleshooting

### High Dashboard Latency

1. Ensure daily aggregates are being updated
2. Check that indexes exist on the usage_events table
3. Consider reducing the time range for trend analysis

### Missing Cost Estimates

1. Verify the provider/model combination has a rate configured
2. Check the provider_pricing table for the model
3. Add a custom rate if needed

### Disk Space Issues

1. Run data cleanup: `POST /api/analytics/maintenance/cleanup`
2. Reduce retention period
3. Consider disabling detailed event storage
