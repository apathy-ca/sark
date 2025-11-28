# Gateway Integration Examples

This directory contains comprehensive examples demonstrating how to properly use the Gateway data models and services for MCP Gateway Integration.

**Author:** Engineer 1 (Gateway Models Architect)
**Created:** 2024
**Purpose:** Educational examples showing best practices for Gateway model usage

---

## 📚 Available Examples

### 1. `basic_client.py` - Gateway Client Basics

**What it demonstrates:**
- Initializing the Gateway client with proper configuration
- Listing available MCP servers
- Filtering servers by sensitivity level
- Getting detailed server information
- Discovering tools on servers
- Health checking the Gateway

**Best for:**
- First-time Gateway users
- Understanding basic client operations
- Learning about server discovery

**Run it:**
```bash
python examples/gateway-integration/basic_client.py
```

**Key Concepts:**
- Using context managers for resource cleanup
- Error handling with custom Gateway exceptions
- Type-safe model usage with Pydantic
- Server filtering and querying

---

### 2. `server_registration.py` - Server Registration

**What it demonstrates:**
- Creating valid `GatewayServerInfo` instances
- Understanding Pydantic validation rules
- Choosing appropriate sensitivity levels
- Configuring team-based access control
- Setting up access restrictions
- Managing server health status

**Best for:**
- Server administrators
- DevOps teams registering new MCP servers
- Understanding access control patterns

**Run it:**
```bash
python examples/gateway-integration/server_registration.py
```

**Key Concepts:**
- Sensitivity level guidelines (LOW, MEDIUM, HIGH, CRITICAL)
- Team-based authorization setup
- Access restriction configuration
- Health status management
- Validation error handling

---

### 3. `tool_invocation.py` - Tool Invocation with Authorization

**What it demonstrates:**
- Creating `GatewayAuthorizationRequest` properly
- Action string validation and formatting
- Filtering sensitive parameters before logging
- Complete authorization flow
- Handling authorization denials
- Capability-based access control

**Best for:**
- Application developers invoking MCP tools
- Understanding authorization patterns
- Implementing secure tool invocation

**Run it:**
```bash
python examples/gateway-integration/tool_invocation.py
```

**Key Concepts:**
- Proper action string formatting (`gateway:tool:invoke`)
- Sensitive parameter filtering using `sensitive_params`
- Authorization request/response flow
- Audit trail correlation with `audit_id`
- Capability matching for access control

---

### 4. `error_handling.py` - Comprehensive Error Handling

**What it demonstrates:**
- Handling Pydantic validation errors
- Network error recovery strategies
- Custom retry logic with exponential backoff
- Authorization failure handling
- Graceful degradation patterns
- Debugging strategies and checklists

**Best for:**
- Production-ready implementations
- Resilient error handling patterns
- Troubleshooting integration issues

**Run it:**
```bash
python examples/gateway-integration/error_handling.py
```

**Key Concepts:**
- Validation error → user-friendly messages
- Retryable vs non-retryable errors
- Exponential backoff (2s, 4s, 8s)
- Fallback to cached data
- Debugging checklists for common issues

---

## 🚀 Quick Start

### Prerequisites

1. **Install dependencies:**
   ```bash
   cd /home/jhenry/Source/GRID/sark
   pip install -e .
   ```

2. **Configure Gateway connection** (optional):
   Create `.env` file:
   ```bash
   GATEWAY_ENABLED=true
   GATEWAY_URL=http://localhost:8080
   GATEWAY_API_KEY=your_api_key_here
   ```

3. **Start the Gateway Registry** (for live examples):
   ```bash
   # If using Docker:
   docker-compose up gateway-registry

   # Or start manually if you have it installed
   ```

### Running Examples

All examples are standalone Python scripts that can be run directly:

```bash
# Run individual example
python examples/gateway-integration/basic_client.py

# Run all examples in sequence
for file in examples/gateway-integration/*.py; do
    echo "Running $file..."
    python "$file"
    echo ""
done
```

---

## 📖 Learning Path

**Recommended order for beginners:**

1. **Start with `basic_client.py`**
   - Learn fundamental client operations
   - Understand server discovery
   - See models in action

2. **Then `server_registration.py`**
   - Learn how servers are registered
   - Understand sensitivity levels
   - See validation in practice

3. **Next `tool_invocation.py`**
   - Learn authorization flow
   - Understand parameter filtering
   - See complete request/response cycle

4. **Finally `error_handling.py`**
   - Learn production-ready patterns
   - Understand error recovery
   - Master debugging techniques

---

## 🎯 Common Use Cases

### "I want to discover available MCP servers"
→ See `basic_client.py` - Example 1 (List Servers)

### "I need to register a new MCP server"
→ See `server_registration.py` - Examples 3-4 (Low/Critical Sensitivity)

### "I want to invoke a tool with authorization"
→ See `tool_invocation.py` - Example 4 (Complete Flow)

### "How do I handle sensitive parameters?"
→ See `tool_invocation.py` - Example 3 (Parameter Filtering)

### "My client is getting timeout errors"
→ See `error_handling.py` - Examples 3-4 (Network Errors, Retry Logic)

### "Authorization is failing - how do I debug?"
→ See `error_handling.py` - Example 7 (Debugging Strategies)

---

## 🛡️ Security Best Practices

These examples demonstrate important security patterns:

✅ **Always filter sensitive parameters** before logging:
```python
filtered_params = filter_sensitive_params(
    raw_params,
    tool_info.sensitive_params
)
```

✅ **Validate authorization before tool invocation**:
```python
auth_response = await authorize_request(auth_request)
if auth_response.allowed:
    # Proceed with tool invocation
```

✅ **Use proper sensitivity levels**:
- `LOW`: Public/non-sensitive data
- `MEDIUM`: Internal business data
- `HIGH`: Sensitive business data (PII, financial)
- `CRITICAL`: Highly regulated or critical infrastructure

✅ **Preserve audit trails**:
```python
# Link audit ID to response
response.audit_id = audit_id
```

---

## 🔧 Troubleshooting

### Example Won't Run

**Error:** `ModuleNotFoundError: No module named 'sark'`
**Fix:** Install package: `pip install -e .`

**Error:** `GatewayConnectionError: Connection refused`
**Fix:** Start Gateway Registry or update `GATEWAY_URL` in `.env`

**Error:** `ValidationError: sensitivity_level`
**Fix:** Use one of: `low`, `medium`, `high`, `critical`

### Examples Run But No Output

- Check that `GATEWAY_ENABLED=true` in your `.env`
- Verify Gateway is running: `curl http://localhost:8080/health`
- Review example code - some intentionally use fake URLs for error demos

---

## 📝 Example Code Style

All examples follow these conventions:

1. **Docstrings** explain what the example demonstrates
2. **Print statements** show execution flow
3. **Try/except blocks** demonstrate error handling
4. **Comments** explain key concepts
5. **Type hints** show proper model usage

**Example structure:**
```python
def example_feature_name():
    """
    Example: Brief description.

    Demonstrates:
    - Point 1
    - Point 2
    """
    print("=" * 60)
    print("Example: Feature Name")
    print("=" * 60)

    # Implementation with comments
    # ...

    print("\n✅ Success message")
```

---

## 🤝 Contributing

To add new examples:

1. Follow the existing naming pattern: `feature_name.py`
2. Include comprehensive docstrings
3. Add examples to this README
4. Ensure examples run standalone
5. Demonstrate both success and failure cases
6. Include debugging guidance

---

## 📚 Related Documentation

- **Gateway Models Reference**: `docs/gateway-integration/MODELS_GUIDE.md`
- **Model Enhancements**: `docs/gateway-integration/MODEL_ENHANCEMENTS.md`
- **Code Reviews**: `docs/gateway-integration/reviews/`
- **API Documentation**: `docs/api/gateway.md`

---

## ❓ Questions or Issues?

If these examples don't cover your use case:

1. Check the comprehensive models guide
2. Review the code review documents for advanced patterns
3. Consult the API documentation
4. Contact Engineer 1 (Gateway Models Architect)

---

**Happy coding! 🚀**
