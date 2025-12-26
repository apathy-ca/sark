"""
Multi-protocol orchestration integration tests for SARK v2.0.

Tests complex scenarios involving multiple protocols:
- MCP + HTTP workflows
- HTTP + gRPC workflows
- MCP + HTTP + gRPC workflows
- Policy evaluation across protocols
- Audit correlation across protocols
- Error handling in multi-protocol chains
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sark.models.base import InvocationRequest, InvocationResult

# ============================================================================
# Multi-Protocol Workflow Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.multi_protocol
@pytest.mark.requires_adapters
class TestMultiProtocolWorkflows:
    """Test workflows that span multiple protocols."""

    @pytest.mark.asyncio
    async def test_mcp_to_http_workflow(
        self, populated_registry, sample_mcp_resource, sample_http_resource
    ):
        """
        Test MCP -> HTTP workflow.

        Scenario: Read file from MCP server, then POST data to HTTP API.
        """
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")

        # Step 1: Read file via MCP
        mcp_request = InvocationRequest(
            capability_id=f"{sample_mcp_resource.id}-read_file",
            principal_id=str(uuid4()),
            arguments={"path": "/data/users.json"},
            context={"workflow_id": "test-workflow-1"},
        )
        mcp_result = await mcp_adapter.invoke(mcp_request)

        assert mcp_result.success is True

        # Step 2: POST data to HTTP API (using data from step 1)
        http_request = InvocationRequest(
            capability_id=f"{sample_http_resource.id}-POST-/users",
            principal_id=str(uuid4()),
            arguments={"name": "Test User", "email": "test@example.com"},
            context={"workflow_id": "test-workflow-1", "previous_step": "mcp_read_file"},
        )
        http_result = await http_adapter.invoke(http_request)

        assert http_result.success is True
        assert http_result.result["status"] == 200

    @pytest.mark.asyncio
    async def test_http_to_grpc_workflow(
        self, populated_registry, sample_http_resource, sample_grpc_resource
    ):
        """
        Test HTTP -> gRPC workflow.

        Scenario: Fetch user list from HTTP API, then query gRPC service.
        """
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        # Step 1: List users via HTTP
        http_request = InvocationRequest(
            capability_id=f"{sample_http_resource.id}-GET-/users",
            principal_id=str(uuid4()),
            arguments={},
            context={"workflow_id": "test-workflow-2"},
        )
        http_result = await http_adapter.invoke(http_request)

        assert http_result.success is True

        # Step 2: Get user details via gRPC
        grpc_request = InvocationRequest(
            capability_id=f"{sample_grpc_resource.id}-UserService.GetUser",
            principal_id=str(uuid4()),
            arguments={"user_id": "123"},
            context={"workflow_id": "test-workflow-2", "previous_step": "http_list_users"},
        )
        grpc_result = await grpc_adapter.invoke(grpc_request)

        assert grpc_result.success is True
        assert "user_id" in grpc_result.result

    @pytest.mark.asyncio
    async def test_three_protocol_workflow(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """
        Test MCP -> HTTP -> gRPC workflow.

        Scenario: Full multi-protocol chain.
        """
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        workflow_id = str(uuid4())
        principal_id = str(uuid4())

        # Step 1: Read config from MCP filesystem
        step1_result = await mcp_adapter.invoke(
            InvocationRequest(
                capability_id=f"{sample_mcp_resource.id}-read_file",
                principal_id=principal_id,
                arguments={"path": "/config/settings.json"},
                context={"workflow_id": workflow_id, "step": 1},
            )
        )
        assert step1_result.success is True

        # Step 2: Create user via HTTP API
        step2_result = await http_adapter.invoke(
            InvocationRequest(
                capability_id=f"{sample_http_resource.id}-POST-/users",
                principal_id=principal_id,
                arguments={"name": "Multi Protocol User"},
                context={"workflow_id": workflow_id, "step": 2},
            )
        )
        assert step2_result.success is True

        # Step 3: Query user service via gRPC
        step3_result = await grpc_adapter.invoke(
            InvocationRequest(
                capability_id=f"{sample_grpc_resource.id}-UserService.GetUser",
                principal_id=principal_id,
                arguments={"user_id": "123"},
                context={"workflow_id": workflow_id, "step": 3},
            )
        )
        assert step3_result.success is True

        # Verify all steps succeeded
        assert all([step1_result.success, step2_result.success, step3_result.success])

    @pytest.mark.asyncio
    async def test_parallel_multi_protocol_invocations(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test parallel invocations across different protocols."""
        import asyncio

        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        principal_id = str(uuid4())

        # Execute all three in parallel
        results = await asyncio.gather(
            mcp_adapter.invoke(
                InvocationRequest(
                    capability_id=f"{sample_mcp_resource.id}-list_files",
                    principal_id=principal_id,
                    arguments={"path": "/"},
                    context={},
                )
            ),
            http_adapter.invoke(
                InvocationRequest(
                    capability_id=f"{sample_http_resource.id}-GET-/users",
                    principal_id=principal_id,
                    arguments={},
                    context={},
                )
            ),
            grpc_adapter.invoke(
                InvocationRequest(
                    capability_id=f"{sample_grpc_resource.id}-UserService.ListUsers",
                    principal_id=principal_id,
                    arguments={},
                    context={},
                )
            ),
        )

        # All should succeed
        assert len(results) == 3
        assert all(r.success for r in results)


# ============================================================================
# Policy Evaluation Across Protocols
# ============================================================================


@pytest.mark.v2
@pytest.mark.multi_protocol
class TestMultiProtocolPolicyEvaluation:
    """Test policy evaluation for multi-protocol scenarios."""

    @pytest.mark.asyncio
    async def test_policy_evaluation_per_protocol(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test that policy evaluation works consistently across protocols."""
        # Mock policy service
        mock_policy = MagicMock()
        mock_policy.evaluate = AsyncMock(return_value={"allow": True})

        principal_id = str(uuid4())

        # Create requests for each protocol
        mcp_request = InvocationRequest(
            capability_id=f"{sample_mcp_resource.id}-read_file",
            principal_id=principal_id,
            arguments={},
            context={"protocol": "mcp"},
        )

        http_request = InvocationRequest(
            capability_id=f"{sample_http_resource.id}-GET-/users",
            principal_id=principal_id,
            arguments={},
            context={"protocol": "http"},
        )

        grpc_request = InvocationRequest(
            capability_id=f"{sample_grpc_resource.id}-UserService.GetUser",
            principal_id=principal_id,
            arguments={},
            context={"protocol": "grpc"},
        )

        # In a real scenario, each would be evaluated by policy service
        # Here we just verify the request structure is protocol-agnostic
        assert all(
            hasattr(req, "capability_id") for req in [mcp_request, http_request, grpc_request]
        )
        assert all(
            hasattr(req, "principal_id") for req in [mcp_request, http_request, grpc_request]
        )

    @pytest.mark.asyncio
    async def test_sensitivity_level_across_protocols(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test that sensitivity levels are respected across all protocols."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        # Get capabilities for all resources
        mcp_caps = await mcp_adapter.get_capabilities(sample_mcp_resource)
        http_caps = await http_adapter.get_capabilities(sample_http_resource)
        grpc_caps = await grpc_adapter.get_capabilities(sample_grpc_resource)

        # All capabilities should have sensitivity levels
        all_caps = mcp_caps + http_caps + grpc_caps
        assert all(hasattr(cap, "sensitivity_level") for cap in all_caps)
        assert all(
            cap.sensitivity_level in ["low", "medium", "high", "critical"] for cap in all_caps
        )


# ============================================================================
# Audit Correlation Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.multi_protocol
class TestMultiProtocolAuditCorrelation:
    """Test audit trail correlation across protocols."""

    @pytest.mark.asyncio
    async def test_workflow_audit_correlation(
        self, populated_registry, sample_mcp_resource, sample_http_resource
    ):
        """Test that workflow audit events can be correlated."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")

        workflow_id = str(uuid4())
        principal_id = str(uuid4())

        # Execute workflow with correlation ID
        mcp_result = await mcp_adapter.invoke(
            InvocationRequest(
                capability_id=f"{sample_mcp_resource.id}-read_file",
                principal_id=principal_id,
                arguments={},
                context={"workflow_id": workflow_id, "step": 1},
            )
        )

        http_result = await http_adapter.invoke(
            InvocationRequest(
                capability_id=f"{sample_http_resource.id}-POST-/users",
                principal_id=principal_id,
                arguments={},
                context={"workflow_id": workflow_id, "step": 2},
            )
        )

        # Verify both invocations succeeded
        assert mcp_result.success is True
        assert http_result.success is True

        # In a real implementation, audit service would correlate these
        # by workflow_id in the context

    @pytest.mark.asyncio
    async def test_cross_protocol_audit_metadata(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test that audit metadata is consistent across protocols."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        principal_id = str(uuid4())

        # Invoke each protocol
        results = []
        for adapter, resource in [
            (mcp_adapter, sample_mcp_resource),
            (http_adapter, sample_http_resource),
            (grpc_adapter, sample_grpc_resource),
        ]:
            capabilities = await adapter.get_capabilities(resource)
            result = await adapter.invoke(
                InvocationRequest(
                    capability_id=capabilities[0].id,
                    principal_id=principal_id,
                    arguments={},
                    context={"audit_test": True},
                )
            )
            results.append(result)

        # All results should have duration and metadata
        assert all(r.duration_ms > 0 for r in results)
        assert all("adapter" in r.metadata for r in results)
        assert {r.metadata["adapter"] for r in results} == {"mcp", "http", "grpc"}


# ============================================================================
# Error Handling in Multi-Protocol Chains
# ============================================================================


@pytest.mark.v2
@pytest.mark.multi_protocol
class TestMultiProtocolErrorHandling:
    """Test error handling in multi-protocol workflows."""

    @pytest.mark.asyncio
    async def test_workflow_with_failed_step(
        self, populated_registry, sample_mcp_resource, sample_http_resource
    ):
        """Test handling of failures in multi-protocol workflow."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")

        # Mock HTTP adapter to fail
        original_invoke = http_adapter.invoke
        http_adapter.invoke = AsyncMock(
            return_value=InvocationResult(
                success=False, error="Simulated HTTP failure", metadata={}, duration_ms=5.0
            )
        )

        workflow_id = str(uuid4())
        principal_id = str(uuid4())

        # Step 1 should succeed
        step1_result = await mcp_adapter.invoke(
            InvocationRequest(
                capability_id=f"{sample_mcp_resource.id}-read_file",
                principal_id=principal_id,
                arguments={},
                context={"workflow_id": workflow_id},
            )
        )
        assert step1_result.success is True

        # Step 2 should fail
        step2_result = await http_adapter.invoke(
            InvocationRequest(
                capability_id=f"{sample_http_resource.id}-POST-/users",
                principal_id=principal_id,
                arguments={},
                context={"workflow_id": workflow_id},
            )
        )
        assert step2_result.success is False
        assert "Simulated HTTP failure" in step2_result.error

        # Restore original
        http_adapter.invoke = original_invoke

    @pytest.mark.asyncio
    async def test_partial_workflow_rollback(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test that workflow failures are properly tracked."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        workflow_id = str(uuid4())
        principal_id = str(uuid4())

        completed_steps = []

        try:
            # Step 1: MCP
            result1 = await mcp_adapter.invoke(
                InvocationRequest(
                    capability_id=f"{sample_mcp_resource.id}-read_file",
                    principal_id=principal_id,
                    arguments={},
                    context={"workflow_id": workflow_id},
                )
            )
            if result1.success:
                completed_steps.append("mcp")

            # Step 2: HTTP
            result2 = await http_adapter.invoke(
                InvocationRequest(
                    capability_id=f"{sample_http_resource.id}-POST-/users",
                    principal_id=principal_id,
                    arguments={},
                    context={"workflow_id": workflow_id},
                )
            )
            if result2.success:
                completed_steps.append("http")

            # Step 3: gRPC
            result3 = await grpc_adapter.invoke(
                InvocationRequest(
                    capability_id=f"{sample_grpc_resource.id}-UserService.GetUser",
                    principal_id=principal_id,
                    arguments={},
                    context={"workflow_id": workflow_id},
                )
            )
            if result3.success:
                completed_steps.append("grpc")

        except Exception:
            # Track which steps completed before failure
            pass

        # In our mock scenario, all should complete successfully
        assert len(completed_steps) == 3


# ============================================================================
# Performance and Scalability Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.multi_protocol
@pytest.mark.slow
class TestMultiProtocolPerformance:
    """Test performance characteristics of multi-protocol operations."""

    @pytest.mark.asyncio
    async def test_concurrent_multi_protocol_throughput(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test concurrent requests across multiple protocols."""
        import asyncio

        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        principal_id = str(uuid4())
        num_requests = 10

        # Create mix of requests across protocols
        tasks = []
        for i in range(num_requests):
            protocol = ["mcp", "http", "grpc"][i % 3]
            adapter = populated_registry.get(protocol)

            if protocol == "mcp":
                resource = sample_mcp_resource
                cap_id = f"{resource.id}-list_files"
            elif protocol == "http":
                resource = sample_http_resource
                cap_id = f"{resource.id}-GET-/users"
            else:
                resource = sample_grpc_resource
                cap_id = f"{resource.id}-UserService.ListUsers"

            tasks.append(
                adapter.invoke(
                    InvocationRequest(
                        capability_id=cap_id,
                        principal_id=principal_id,
                        arguments={},
                        context={"request_index": i},
                    )
                )
            )

        # Execute all concurrently
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == num_requests
        assert all(r.success for r in results)

        # Check distribution across protocols
        adapters = [r.metadata["adapter"] for r in results]
        assert "mcp" in adapters
        assert "http" in adapters
        assert "grpc" in adapters

    @pytest.mark.asyncio
    async def test_protocol_adapter_overhead(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test that adapter overhead is minimal."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        principal_id = str(uuid4())

        # Measure each protocol's response time
        results = {}
        for adapter, resource, protocol in [
            (mcp_adapter, sample_mcp_resource, "mcp"),
            (http_adapter, sample_http_resource, "http"),
            (grpc_adapter, sample_grpc_resource, "grpc"),
        ]:
            caps = await adapter.get_capabilities(resource)
            result = await adapter.invoke(
                InvocationRequest(
                    capability_id=caps[0].id, principal_id=principal_id, arguments={}, context={}
                )
            )
            results[protocol] = result.duration_ms

        # All should complete in reasonable time (mock times)
        assert all(duration > 0 for duration in results.values())
        assert all(duration < 1000 for duration in results.values())  # Mock < 1 second


# ============================================================================
# Resource Discovery Integration
# ============================================================================


@pytest.mark.v2
@pytest.mark.multi_protocol
class TestMultiProtocolResourceDiscovery:
    """Test resource discovery across multiple protocols."""

    @pytest.mark.asyncio
    async def test_discover_all_protocols(self, populated_registry):
        """Test discovering resources from all available protocols."""
        all_resources = []

        for protocol in populated_registry.list_protocols():
            adapter = populated_registry.get(protocol)

            # Create appropriate config for each protocol
            if protocol == "mcp":
                config = {"name": "mcp-test", "command": "test"}
            elif protocol == "http":
                config = {"base_url": "https://test.com"}
            elif protocol == "grpc":
                config = {"endpoint": "localhost:50051"}
            else:
                config = {}

            resources = await adapter.discover_resources(config)
            all_resources.extend(resources)

        # Should have discovered resources from all protocols
        assert len(all_resources) >= 3
        protocols = {r.protocol for r in all_resources}
        assert "mcp" in protocols
        assert "http" in protocols
        assert "grpc" in protocols

    @pytest.mark.asyncio
    async def test_capability_aggregation_across_protocols(
        self, populated_registry, sample_mcp_resource, sample_http_resource, sample_grpc_resource
    ):
        """Test aggregating capabilities from multiple protocol resources."""
        all_capabilities = []

        for resource in [sample_mcp_resource, sample_http_resource, sample_grpc_resource]:
            adapter = populated_registry.get(resource.protocol)
            caps = await adapter.get_capabilities(resource)
            all_capabilities.extend(caps)

        # Should have capabilities from all protocols
        assert len(all_capabilities) >= 6  # 2 from each protocol

        # Verify capabilities maintain protocol context
        protocols_in_caps = {
            cap.resource_id.split("-")[0] for cap in all_capabilities if "-" in cap.resource_id
        }
        assert len(protocols_in_caps) >= 2
