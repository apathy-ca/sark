# SARK v2.0 Integration Tests

This directory contains comprehensive integration tests for SARK v2.0 features, focusing on protocol adapters, multi-protocol orchestration, and federation capabilities.

## Overview

SARK v2.0 introduces protocol-agnostic governance through the ProtocolAdapter interface, enabling support for MCP, HTTP/REST, gRPC, and custom protocols. These integration tests validate:

- **Adapter Functionality**: Resource discovery, capability enumeration, invocation, health checks
- **Multi-Protocol Orchestration**: Workflows spanning multiple protocols
- **Federation**: Cross-organization authorization and resource sharing
- **Chaos Engineering**: Resilience under adverse conditions

## Test Structure

```
tests/integration/v2/
├── conftest.py                      # Shared fixtures and mock adapters
├── test_adapter_integration.py      # Adapter interface compliance tests
├── test_multi_protocol.py           # Multi-protocol orchestration tests
├── test_federation_flow.py          # Federation integration tests
└── README.md                        # This file

tests/chaos/
└── test_federation_chaos.py         # Chaos engineering tests for federation
```

## Test Categories

### 1. Adapter Integration Tests (`test_adapter_integration.py`)

Tests the ProtocolAdapter interface implementation across all supported protocols.

**Test Classes:**
- `TestAdapterRegistry`: Registry management and adapter lookup
- `TestMCPAdapter`: MCP protocol adapter functionality
- `TestHTTPAdapter`: HTTP/REST adapter functionality
- `TestGRPCAdapter`: gRPC adapter functionality
- `TestCrossAdapterIntegration`: Cross-adapter scenarios
- `TestAdapterLifecycle`: Lifecycle hooks and management
- `TestAdapterErrorHandling`: Error handling and fallbacks
- `TestAdapterSARKCoreIntegration`: Integration with SARK core

**Key Scenarios:**
- Adapter registration and discovery
- Resource discovery across protocols
- Capability enumeration
- Request validation
- Capability invocation (including streaming for gRPC)
- Health checking
- Feature matrix (streaming, batch support)

**Run adapter tests:**
```bash
pytest tests/integration/v2/test_adapter_integration.py -v -m "adapter"
```

### 2. Multi-Protocol Orchestration Tests (`test_multi_protocol.py`)

Tests complex workflows that span multiple protocols.

**Test Classes:**
- `TestMultiProtocolWorkflows`: Sequential and parallel multi-protocol workflows
- `TestMultiProtocolPolicyEvaluation`: Policy evaluation across protocols
- `TestMultiProtocolAuditCorrelation`: Audit trail correlation
- `TestMultiProtocolErrorHandling`: Error handling in multi-protocol chains
- `TestMultiProtocolPerformance`: Performance characteristics
- `TestMultiProtocolResourceDiscovery`: Resource aggregation

**Key Scenarios:**
- MCP → HTTP workflows
- HTTP → gRPC workflows
- MCP → HTTP → gRPC three-protocol chains
- Parallel invocations across protocols
- Sensitivity level enforcement
- Workflow audit correlation
- Partial workflow failure handling
- Concurrent multi-protocol throughput

**Run multi-protocol tests:**
```bash
pytest tests/integration/v2/test_multi_protocol.py -v -m "multi_protocol"
```

### 3. Federation Flow Tests (`test_federation_flow.py`)

Tests cross-organization federation capabilities.

**Test Classes:**
- `TestFederationNodeDiscovery`: Node discovery via DNS-SD and static config
- `TestMTLSTrustEstablishment`: mTLS trust and certificate validation
- `TestCrossOrgAuthorization`: Cross-org authorization flows
- `TestFederatedResourceLookup`: Federated resource discovery
- `TestFederationAuditCorrelation`: Cross-org audit correlation
- `TestFederationErrorHandling`: Federation error handling
- `TestMultiNodeFederation`: Multi-node scenarios
- `TestFederationPerformance`: Federation performance

**Key Scenarios:**
- Static and DNS-based node discovery
- mTLS trust establishment
- Certificate validation and rotation
- Cross-org authorization requests
- Federated resource queries
- Audit event correlation across orgs
- Node failure handling
- Certificate expiration and revocation
- Three-way federation chains
- Federation mesh topology

**Run federation tests:**
```bash
pytest tests/integration/v2/test_federation_flow.py -v -m "federation"
```

### 4. Chaos Engineering Tests (`test_federation_chaos.py`)

Tests federation resilience under adverse conditions.

**Test Classes:**
- `TestFederationNetworkPartitions`: Network partition scenarios
- `TestFederationNodeFailures`: Node crash and failure scenarios
- `TestFederationCertificateChaos`: Certificate-related failures
- `TestFederationByzantineFailures`: Byzantine fault scenarios
- `TestFederationSplitBrain`: Split-brain scenarios
- `TestFederationRecovery`: Recovery and resilience mechanisms
- `TestFederationLoadChaos`: Load and stress scenarios

**Key Scenarios:**
- Complete network partitions
- Partial network partitions
- Intermittent connectivity (flapping)
- Sudden node crashes
- Graceful node shutdowns
- Cascading failures
- Certificate expiration mid-operation
- Certificate revocation
- CA certificate rotation
- MITM attack detection
- Malformed responses
- Contradictory responses
- Slow-sending nodes (slowloris)
- Resource exhaustion attacks
- Split-brain scenarios
- Automatic retry with exponential backoff
- Circuit breaker patterns
- Fallback to cached decisions
- Load spikes and rate limiting
- Thundering herd scenarios

**Run chaos tests:**
```bash
pytest tests/chaos/test_federation_chaos.py -v -m "chaos"
```

## Running Tests

### Prerequisites

1. **Python 3.11+** with Poetry installed
2. **Docker and Docker Compose** for multi-node testing
3. **Mock protocol servers** (started via docker-compose)

### Quick Start

```bash
# Install dependencies
poetry install --with dev,test

# Run all v2.0 integration tests
pytest tests/integration/v2 tests/chaos -v -m "v2"

# Run specific test categories
pytest -v -m "adapter"        # Adapter tests only
pytest -v -m "multi_protocol" # Multi-protocol tests only
pytest -v -m "federation"     # Federation tests only
pytest -v -m "chaos"          # Chaos tests only
```

### Using Docker Compose

For tests requiring multiple SARK nodes or mock services:

```bash
# Start the complete v2.0 test environment
docker-compose -f docker-compose.v2-testing.yml up -d

# Wait for services to be ready
sleep 30

# Run tests
poetry run pytest tests/integration/v2 tests/chaos -v

# Cleanup
docker-compose -f docker-compose.v2-testing.yml down -v
```

### Test Environment Variables

```bash
export SARK_NODE_A_URL=http://localhost:8000
export SARK_NODE_B_URL=http://localhost:8001
export SARK_NODE_C_URL=http://localhost:8002
export PYTEST_ARGS="-v --tb=short"
```

## Test Fixtures

### Mock Adapters

The test suite includes mock implementations of all protocol adapters:

- `MockMCPAdapter`: Simulates MCP server interactions
- `MockHTTPAdapter`: Simulates HTTP/REST API calls
- `MockGRPCAdapter`: Simulates gRPC service calls (including streaming)

These mocks provide predictable behavior for testing without requiring actual protocol servers.

### Federation Fixtures

- `mock_federation_node`: Simulates a remote federation node
- `mock_federation_service`: Simulates the federation service
- `populated_registry`: Adapter registry with all adapters registered
- `multi_protocol_scenario`: Pre-configured multi-protocol workflow

### Resource Fixtures

- `sample_mcp_resource`: Example MCP filesystem server
- `sample_http_resource`: Example GitHub API resource
- `sample_grpc_resource`: Example User Management gRPC service
- `sample_capability`: Generic capability for testing
- `sample_invocation_request`: Example invocation request

## Test Markers

Tests are marked with the following pytest markers:

- `@pytest.mark.v2`: All v2.0 tests
- `@pytest.mark.adapter`: Adapter-specific tests
- `@pytest.mark.multi_protocol`: Multi-protocol orchestration tests
- `@pytest.mark.federation`: Federation tests
- `@pytest.mark.chaos`: Chaos engineering tests
- `@pytest.mark.requires_adapters`: Tests requiring all adapters
- `@pytest.mark.slow`: Long-running tests (>5 seconds)

**Filter by markers:**
```bash
pytest -v -m "v2 and adapter"
pytest -v -m "v2 and not slow"
pytest -v -m "federation and not chaos"
```

## Coverage Goals

- **Adapter Tests**: >90% coverage of `src/sark/adapters/`
- **Federation Tests**: >85% coverage of `src/sark/federation/`
- **Overall v2.0**: >85% coverage of v2.0 features

**Generate coverage report:**
```bash
pytest tests/integration/v2 tests/chaos \
  --cov=src/sark/adapters \
  --cov=src/sark/federation \
  --cov-report=html \
  --cov-report=term-missing
```

## CI/CD Integration

Tests are automatically run via GitHub Actions on:

- Push to `main`, `feat/v2*`, `release/v2*` branches
- Pull requests targeting `main` or `feat/v2*` branches
- Manual workflow dispatch with configurable scope

**CI Workflow:** `.github/workflows/v2-integration-tests.yml`

**Test Jobs:**
1. `adapter-tests`: Matrix tests for each adapter (MCP, HTTP, gRPC)
2. `multi-protocol-tests`: Multi-protocol orchestration tests
3. `federation-tests`: Federation flow tests with 3 SARK nodes
4. `chaos-tests`: Chaos engineering tests
5. `full-integration-suite`: Complete test suite on `main` branch
6. `test-summary`: Aggregated test results and reporting

## Troubleshooting

### Common Issues

**1. Tests fail with "adapter not registered"**
```bash
# Ensure adapters are properly registered
export FEATURE_PROTOCOL_ADAPTERS=true
```

**2. Federation tests timeout**
```bash
# Increase health check timeout
export FEDERATION_HEALTH_CHECK_TIMEOUT=60
```

**3. Docker services not starting**
```bash
# Check docker-compose logs
docker-compose -f docker-compose.v2-testing.yml logs

# Restart with fresh volumes
docker-compose -f docker-compose.v2-testing.yml down -v
docker-compose -f docker-compose.v2-testing.yml up -d
```

**4. Mock gRPC service fails**
```bash
# Rebuild mock gRPC service
docker-compose -f docker-compose.v2-testing.yml build mock-grpc-service
```

### Debug Mode

Run tests with verbose logging:

```bash
pytest tests/integration/v2 \
  -v \
  --log-cli-level=DEBUG \
  --tb=long \
  -s
```

## Contributing

When adding new v2.0 integration tests:

1. **Use existing fixtures** from `conftest.py` when possible
2. **Mark tests appropriately** with `@pytest.mark.v2` and other relevant markers
3. **Follow naming conventions**: `test_<feature>_<scenario>`
4. **Document test scenarios** in docstrings
5. **Ensure cleanup** in fixtures with `yield` and proper teardown
6. **Target >85% coverage** for new adapter/federation code

## Dependencies

Required for engineer-1 adapter implementation:
- `engineer-1.mcp-adapter`: MCP adapter must be complete before full test suite runs

## Related Documentation

- **Protocol Adapter Spec**: `docs/v2.0/PROTOCOL_ADAPTER_SPEC.md`
- **Federation Spec**: `docs/v2.0/FEDERATION_SPEC.md`
- **Implementation Plan**: `../claude-orchestrator/SARK_v2.0_ORCHESTRATED_IMPLEMENTATION_PLAN.md`
- **Adapter Development Guide**: `docs/v2.0/ADAPTER_DEVELOPMENT_GUIDE.md`

## Test Statistics

As of Week 2-7 of v2.0 implementation:

- **Total Test Files**: 4
- **Total Test Classes**: ~30
- **Total Test Methods**: ~150+
- **Estimated Coverage**: Target 85%+
- **Estimated Runtime**: ~5-10 minutes (full suite with docker-compose)

## Contact

**Test Owner**: QA-1 (Integration Testing Lead)
**Timeline**: Weeks 2-7 of v2.0 implementation
**Priority**: High
**Workstream**: Quality
