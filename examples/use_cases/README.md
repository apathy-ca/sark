# MCP Use Case Examples

This directory contains real-world MCP server use case examples showing how SARK governs different types of MCP tools and workflows.

## Overview

Each JSON file represents a complete MCP server specification including:
- Server configuration and metadata
- Tool definitions with detailed parameters
- Example requests and responses
- OPA policy examples
- Deployment configurations
- Benefits and limitations
- Real-world scenarios

## Use Cases

### 1. Database Query Tool ([01_database_query_tool.json](01_database_query_tool.json))

**Purpose:** Secure database access for AI assistants and analysts

**Key Features:**
- Read-only query execution (SELECT only)
- Multiple database support (PostgreSQL, MySQL, Snowflake)
- Automatic PII redaction
- Query validation and timeout enforcement
- Result caching for performance

**Target Users:**
- Data analysts
- AI assistants answering data questions
- BI tools and dashboards

**Example Query:**
```json
{
  "tool": "query_postgres",
  "arguments": {
    "query": "SELECT COUNT(*) FROM users WHERE status = 'active'",
    "database": "analytics",
    "limit": 1000
  }
}
```

**Security Highlights:**
- Prevents DDL/DML operations (no DELETE, UPDATE, DROP)
- Sensitivity-based access control (production DB requires DBA role)
- Complete audit trail of all queries
- PII columns automatically redacted in results

---

### 2. Ticket Creation ([02_ticket_creation.json](02_ticket_creation.json))

**Purpose:** Unified ticketing interface for Jira and ServiceNow

**Key Features:**
- Create tickets in Jira and ServiceNow
- Automatic ticket routing based on labels/components
- SLA tracking and breach alerts
- Template-based ticket creation
- Search and update existing tickets

**Target Users:**
- Employees reporting issues
- AI assistants creating tickets from conversations
- IT operations teams

**Example - Create Jira Bug:**
```json
{
  "tool": "create_jira_ticket",
  "arguments": {
    "project": "ENG",
    "issue_type": "Bug",
    "summary": "API returning 500 errors",
    "description": "Production API failing...",
    "priority": "Critical",
    "labels": ["production", "api", "p0"]
  }
}
```

**Automation Benefits:**
- AI can create tickets from natural language descriptions
- Automatic assignment to correct team based on labels
- SLA calculation and tracking
- Integration with existing ITSM workflows

---

### 3. Document Search ([03_document_search.json](03_document_search.json))

**Purpose:** Intelligent document search across Confluence, SharePoint, Google Docs

**Key Features:**
- Hybrid search (keyword + semantic)
- AI-powered question answering with citations (RAG)
- Document summarization
- Access control enforcement from source systems
- Real-time indexing (updates within minutes)

**Target Users:**
- Employees looking for company information
- AI assistants answering questions from company knowledge base
- New employees during onboarding

**Example - Ask a Question:**
```json
{
  "tool": "ask_question",
  "arguments": {
    "question": "How do I request PTO?",
    "sources": ["confluence"],
    "include_citations": true
  }
}
```

**Response:**
```json
{
  "answer": "To request PTO: 1. Log into BambooHR 2. Navigate to Time Off...",
  "sources_used": [
    {
      "title": "PTO Policy and Procedures",
      "url": "https://company.atlassian.net/wiki/...",
      "relevance": "primary source"
    }
  ]
}
```

**AI Use Case:**
- Employee asks AI assistant "How do I request PTO?"
- AI uses this MCP tool to search company docs
- AI provides accurate answer with source citations
- Reduces time from "searching for 30 minutes" to "instant answer"

---

### 4. Data Analysis Workflow ([04_data_analysis_workflow.json](04_data_analysis_workflow.json))

**Purpose:** Comprehensive data analysis platform for AI-assisted analytics

**Key Features:**
- Load data from multiple sources (databases, S3, files)
- Statistical analysis (descriptive stats, correlations, distributions)
- A/B test analysis with statistical significance testing
- Data visualization (charts, graphs, heatmaps)
- Automated report generation (PDF, PowerPoint)
- SSE transport for streaming progress updates

**Target Users:**
- Data analysts automating routine reports
- Data scientists performing exploratory analysis
- Product managers analyzing A/B test results
- AI assistants generating data insights

**Example - Complete Workflow:**
```json
{
  "workflow": [
    {
      "step": 1,
      "tool": "load_dataset",
      "arguments": {
        "source_type": "snowflake",
        "query": "SELECT * FROM sales WHERE date >= '2024-01-01'"
      }
    },
    {
      "step": 2,
      "tool": "analyze_dataset",
      "arguments": {
        "dataset_id": "from_step_1",
        "analysis_types": ["descriptive_stats", "trends"]
      }
    },
    {
      "step": 3,
      "tool": "create_visualization",
      "arguments": {
        "chart_type": "line",
        "x_column": "date",
        "y_column": "revenue"
      }
    },
    {
      "step": 4,
      "tool": "generate_report",
      "arguments": {
        "title": "Monthly Sales Report",
        "format": "pdf"
      }
    }
  ]
}
```

**Automation Benefits:**
- Reduces monthly reporting from 4 hours to 5 minutes
- AI generates insights automatically
- Professional, publication-ready reports
- Complete reproducibility via audit trail

---

## Common Patterns

### Security & Authorization

All use cases demonstrate:

1. **Sensitivity-Based Access Control**
   ```json
   {
     "sensitivity_level": "high",
     "requires_approval": false
   }
   ```

2. **OPA Policy Integration**
   ```rego
   package mcp.database_query

   default allow := false

   allow if {
     "data_analyst" in input.user.roles
     input.tool.name == "query_postgres"
   }
   ```

3. **Audit Logging**
   - Every tool invocation logged
   - User attribution
   - Parameters captured (with sensitive data redacted)
   - Results summarized
   - Forwarded to SIEM

### Tool Parameter Design

Best practices demonstrated:

1. **Clear Parameter Descriptions**
   ```json
   {
     "query": {
       "type": "string",
       "description": "SQL SELECT query to execute. Must be read-only.",
       "examples": ["SELECT * FROM users LIMIT 100"]
     }
   }
   ```

2. **Validation Constraints**
   ```json
   {
     "limit": {
       "type": "integer",
       "minimum": 1,
       "maximum": 10000,
       "default": 1000
     }
   }
   ```

3. **Enums for Restricted Values**
   ```json
   {
     "priority": {
       "type": "string",
       "enum": ["Blocker", "Critical", "High", "Medium", "Low"]
     }
   }
   ```

### Error Handling

All tools include comprehensive error handling:

```json
{
  "error_handling": {
    "syntax_error": "Returns detailed SQL syntax error message",
    "timeout": "Returns error after 30 seconds with partial results",
    "permission_denied": "Returns 403 with specific resource denied",
    "connection_error": "Retries 3 times with exponential backoff"
  }
}
```

## Using These Examples

### 1. Register a Server

Use the MCP server configuration to register with SARK:

```bash
# Extract server config
jq '.mcp_server' 01_database_query_tool.json > server_config.json

# Register with SARK
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @server_config.json
```

### 2. Deploy OPA Policies

Extract and deploy the OPA policy:

```bash
# Extract policy
jq -r '.opa_policy_example.policy' 01_database_query_tool.json > database_policy.rego

# Deploy to OPA
curl -X PUT http://localhost:8181/v1/policies/database_query \
  -H "Content-Type: text/plain" \
  --data-binary @database_policy.rego
```

### 3. Test Tool Invocation

Use the examples to test tools:

```bash
# Extract example
jq '.tools[0].examples[0]' 01_database_query_tool.json

# Invoke tool
curl -X POST http://localhost:8000/api/v1/tools/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "YOUR_TOOL_ID",
    "arguments": {
      "query": "SELECT * FROM users LIMIT 10",
      "database": "analytics"
    }
  }'
```

### 4. Study for Your Own Implementation

These examples serve as templates for building your own MCP servers:

1. **Copy structure** - Follow the JSON schema
2. **Adapt tools** - Define tools specific to your domain
3. **Define policies** - Write OPA policies for your access control requirements
4. **Test thoroughly** - Use the example patterns for comprehensive testing

## Benefits Summary

| Use Case | Time Saved | Automation Rate | Compliance |
|----------|------------|-----------------|------------|
| Database Query | Hours → Seconds | 80% of queries automated | SOC 2, GDPR, HIPAA |
| Ticket Creation | 5 min → 30 sec | 65% tickets by AI | ITSM workflow compliant |
| Document Search | 30 min → Instant | N/A (instant retrieval) | Access control enforced |
| Data Analysis | 4 hours → 5 min | 100% automation possible | Full audit trail |

## Key Takeaways

1. **MCP servers can govern diverse operations** - from database queries to complex analytics workflows

2. **Security is built-in** - All examples show sensitivity levels, approval requirements, and OPA policies

3. **Audit everything** - Complete audit trails enable compliance (SOC 2, ISO 27001, etc.)

4. **AI-friendly** - Tools designed for AI assistants to use via natural language

5. **Production-ready** - Examples include error handling, retry logic, caching, and performance optimization

6. **Composable** - Tools can be chained into complex workflows (see Example 2 in interactive examples)

## Next Steps

1. **Read the examples** to understand MCP server patterns
2. **Try interactive examples** in `examples/` directory
3. **Study OPA policies** to understand authorization patterns
4. **Build your own MCP server** using these as templates
5. **Register with SARK** for governance and audit

## Related Documentation

- [MCP Architecture Diagram](../../docs/diagrams/01_mcp_architecture.md)
- [Tool Invocation Flow](../../docs/diagrams/02_tool_invocation_flow.md)
- [Interactive Examples](../README.md)
- [OPA Policy Guide](../../docs/OPA_POLICY_GUIDE.md)
- [API Reference](../../docs/API_REFERENCE.md)

## Questions?

See [FAQ](../../docs/FAQ.md) or [GLOSSARY](../../docs/GLOSSARY.md) for common questions and terminology.
