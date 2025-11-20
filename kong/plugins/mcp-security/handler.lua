-- MCP Security Plugin for Kong Gateway
-- Validates MCP protocol and enforces security policies via OPA

local http = require "resty.http"
local cjson = require "cjson.safe"

local MCPSecurityHandler = {
  VERSION = "1.0.0",
  PRIORITY = 1000,
}

function MCPSecurityHandler:access(conf)
  -- Validate MCP protocol version
  local mcp_version = kong.request.get_header("MCP-Version")

  if not mcp_version then
    return kong.response.exit(400, {
      error = "Missing MCP-Version header",
      code = "MCP_VERSION_REQUIRED"
    })
  end

  if mcp_version ~= "2025-06-18" then
    return kong.response.exit(400, {
      error = "Unsupported MCP version: " .. mcp_version,
      code = "MCP_VERSION_UNSUPPORTED",
      supported_versions = {"2025-06-18"}
    })
  end

  -- Extract request body for tool invocation
  local body, err = kong.request.get_body()
  if err then
    kong.log.err("Failed to get request body: ", err)
    return kong.response.exit(400, {
      error = "Invalid request body",
      code = "INVALID_REQUEST_BODY"
    })
  end

  -- Parse JSON body
  local json_body = cjson.decode(body)
  if not json_body then
    return kong.response.exit(400, {
      error = "Invalid JSON body",
      code = "INVALID_JSON"
    })
  end

  -- Extract tool information
  local tool_name = json_body.params and json_body.params.name
  if not tool_name then
    -- Not a tool invocation, allow through
    return
  end

  -- Get authenticated consumer (assumes authentication plugin ran first)
  local consumer = kong.client.get_consumer()
  if not consumer then
    return kong.response.exit(401, {
      error = "Authentication required",
      code = "AUTHENTICATION_REQUIRED"
    })
  end

  -- Query OPA for authorization decision
  local allowed, reason = self:check_opa_policy(conf, consumer, tool_name)

  if not allowed then
    kong.log.warn("Authorization denied for user ", consumer.id, " tool ", tool_name, ": ", reason)
    return kong.response.exit(403, {
      error = "Access denied",
      code = "AUTHORIZATION_DENIED",
      reason = reason
    })
  end

  -- Generate audit ID for request tracking
  local audit_id = kong.uuid()

  -- Inject audit context into upstream request
  kong.service.request.set_header("X-SARK-Audit-ID", audit_id)
  kong.service.request.set_header("X-SARK-User-ID", consumer.id)
  kong.service.request.set_header("X-SARK-Tool-Name", tool_name)

  kong.log.info("Authorization granted for user ", consumer.id, " tool ", tool_name, " audit_id ", audit_id)
end

function MCPSecurityHandler:check_opa_policy(conf, consumer, tool_name)
  local httpc = http.new()
  httpc:set_timeout(conf.opa_timeout or 1000)

  -- Build OPA input
  local opa_input = {
    input = {
      user = {
        id = consumer.id,
        username = consumer.username,
        -- TODO: Add role and teams from consumer metadata
        role = "developer",
        teams = {}
      },
      action = "tool:invoke",
      tool = {
        name = tool_name,
        -- TODO: Look up tool metadata from registry
        sensitivity_level = "medium",
        owner = nil,
        managers = {}
      },
      context = {
        timestamp = ngx.time()
      }
    }
  }

  local body = cjson.encode(opa_input)
  if not body then
    kong.log.err("Failed to encode OPA input")
    return false, "Internal error encoding policy request"
  end

  -- Query OPA
  local res, err = httpc:request_uri(conf.opa_url .. "/v1/data/mcp/allow", {
    method = "POST",
    body = body,
    headers = {
      ["Content-Type"] = "application/json",
    },
  })

  httpc:close()

  if not res then
    kong.log.err("Failed to query OPA: ", err)
    -- Fail closed - deny on error
    return false, "Policy evaluation failed"
  end

  if res.status ~= 200 then
    kong.log.err("OPA returned non-200 status: ", res.status)
    return false, "Policy evaluation error"
  end

  -- Parse OPA response
  local result = cjson.decode(res.body)
  if not result then
    kong.log.err("Failed to parse OPA response")
    return false, "Invalid policy response"
  end

  -- Check decision
  local allow = result.result and result.result.allow or false
  local reason = result.result and result.result.audit_reason or "No reason provided"

  return allow, reason
end

return MCPSecurityHandler
