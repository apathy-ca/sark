"""
HTTP Adapter OpenAPI Discovery Example

This example demonstrates automatic capability discovery from OpenAPI specs.

We'll use PetStore API, a standard OpenAPI example.

Version: 2.0.0
Engineer: ENGINEER-2
"""

import asyncio

from sark.adapters.http import HTTPAdapter


async def main():
    """OpenAPI discovery example."""

    print("=" * 60)
    print("HTTP Adapter - OpenAPI Discovery Example")
    print("=" * 60)

    # Step 1: Create HTTP adapter
    print("\n1. Creating HTTP adapter for PetStore API...")
    adapter = HTTPAdapter(
        base_url="https://petstore3.swagger.io/api/v3",
        auth_config={"type": "none"},
        timeout=10.0,
    )

    print(f"   ✓ Adapter created: {adapter}")

    # Step 2: Auto-discover resource from OpenAPI spec
    print("\n2. Auto-discovering resource from OpenAPI spec...")
    print("   Looking for OpenAPI spec at common paths...")

    try:
        resources = await adapter.discover_resources({
            "base_url": "https://petstore3.swagger.io/api/v3",
            "openapi_spec_url": "https://petstore3.swagger.io/api/v3/openapi.json",
        })

        if resources:
            resource = resources[0]
            print(f"   ✓ Discovered resource: {resource.name}")
            print(f"   - ID: {resource.id}")
            print(f"   - Protocol: {resource.protocol}")
            print(f"   - Endpoint: {resource.endpoint}")
            print(f"   - API Version: {resource.metadata.get('api_version', 'N/A')}")
            print(f"   - OpenAPI Version: {resource.metadata.get('openapi_version', 'N/A')}")
            print(f"   - Description: {resource.metadata.get('description', 'N/A')[:100]}...")
        else:
            print("   ⚠ No resources discovered")
            return

    except Exception as e:
        print(f"   ✗ Discovery failed: {e}")
        print("\n   Note: This is a demo. The PetStore API may not be available.")
        return

    # Step 3: Discover capabilities from OpenAPI spec
    print("\n3. Discovering capabilities from OpenAPI spec...")
    print("   Parsing paths and operations...")

    try:
        capabilities = await adapter.get_capabilities(resource)

        print(f"   ✓ Discovered {len(capabilities)} capabilities!")
        print("\n   Sample capabilities:")

        # Show first 10 capabilities
        for i, cap in enumerate(capabilities[:10], 1):
            method = cap.metadata.get("http_method", "?")
            path = cap.metadata.get("http_path", "?")
            tags = cap.metadata.get("tags", [])

            print(f"\n   [{i}] {cap.name}")
            print(f"       Method: {method}")
            print(f"       Path: {path}")
            print(f"       Tags: {', '.join(tags) if tags else 'None'}")
            print(f"       Description: {cap.description[:80]}..." if len(cap.description) > 80 else f"       Description: {cap.description}")
            print(f"       Sensitivity: {cap.sensitivity_level}")

        if len(capabilities) > 10:
            print(f"\n   ... and {len(capabilities - 10)} more capabilities")

    except Exception as e:
        print(f"   ✗ Capability discovery failed: {e}")
        return

    # Step 4: Examine input/output schemas
    print("\n4. Examining capability schemas...")

    if capabilities:
        # Pick an interesting capability (e.g., POST /pet)
        create_pet_caps = [c for c in capabilities if "post" in c.name.lower() and "pet" in c.name.lower()]

        if create_pet_caps:
            cap = create_pet_caps[0]
            print(f"\n   Example: {cap.name}")
            print(f"   Description: {cap.description}")

            print("\n   Input Schema:")
            input_props = cap.input_schema.get("properties", {})
            required = cap.input_schema.get("required", [])

            for prop_name, prop_schema in list(input_props.items())[:5]:
                req_marker = "* " if prop_name in required else "  "
                prop_type = prop_schema.get("type", "unknown")
                prop_desc = prop_schema.get("description", "")
                print(f"     {req_marker}{prop_name}: {prop_type}")
                if prop_desc:
                    print(f"        {prop_desc[:70]}...")

            if len(input_props) > 5:
                print(f"     ... and {len(input_props) - 5} more properties")

            print("\n   Output Schema:")
            output_type = cap.output_schema.get("type", "unknown")
            print(f"     Type: {output_type}")

            if output_type == "object":
                output_props = cap.output_schema.get("properties", {})
                print(f"     Properties: {len(output_props)}")
                for prop_name in list(output_props.keys())[:5]:
                    print(f"       - {prop_name}")

    # Step 5: Show discovery metadata
    print("\n5. Discovery metadata...")
    print(f"   Resource created: {resource.created_at}")
    print(f"   Resource updated: {resource.updated_at}")
    print(f"   Sensitivity level: {resource.sensitivity_level}")
    print(f"   OpenAPI spec URL: {resource.metadata.get('openapi_spec_url', 'N/A')}")

    servers = resource.metadata.get("servers", [])
    if servers:
        print("\n   Available servers:")
        for server in servers:
            url = server.get("url", "unknown")
            desc = server.get("description", "")
            print(f"     - {url}")
            if desc:
                print(f"       {desc}")

    # Step 6: Cleanup
    print("\n6. Cleaning up...")
    await adapter.on_resource_unregistered(resource)
    print("   ✓ Adapter cleaned up")

    print("\n" + "=" * 60)
    print("Discovery completed!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. OpenAPI specs enable automatic resource discovery")
    print("2. Each operation becomes a governed capability")
    print("3. Input/output schemas are extracted for validation")
    print("4. Sensitivity levels are assigned automatically")
    print("5. No manual capability definition needed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
