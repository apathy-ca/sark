/**
 * SARK API Type Definitions
 * Auto-generated from API documentation
 */

// ============================================================================
// Authentication
// ============================================================================

export interface User {
  user_id: string; // UUID
  username: string;
  email: string;
  roles: string[];
  teams: string[];
  permissions: string[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string;
  user: User;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface LogoutResponse {
  success: boolean;
  message: string;
}

// ============================================================================
// MCP Servers
// ============================================================================

export type TransportType = "http" | "stdio" | "sse";
export type ServerStatus = "active" | "inactive" | "error";
export type SensitivityLevel = "low" | "medium" | "high" | "critical";

export interface Tool {
  id: string; // UUID
  name: string;
  description: string | null;
  parameters: Record<string, any>; // JSON Schema
  sensitivity_level: SensitivityLevel;
  requires_approval: boolean;
  created_at: string; // ISO 8601
}

export interface Server {
  id: string; // UUID
  name: string;
  description: string | null;
  transport: TransportType;
  endpoint: string | null;
  command: string | null;
  status: ServerStatus;
  sensitivity_level: SensitivityLevel;
  tools: Tool[];
  metadata: Record<string, any>;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface ServerListItem {
  id: string;
  name: string;
  transport: TransportType;
  status: ServerStatus;
  sensitivity_level: SensitivityLevel;
  created_at: string;
}

export interface ToolDefinition {
  name: string;
  description?: string;
  parameters?: Record<string, any>;
  sensitivity_level?: SensitivityLevel;
  signature?: string;
  requires_approval?: boolean;
}

export interface ServerRegistrationRequest {
  name: string;
  transport: TransportType;
  endpoint?: string;
  command?: string;
  version?: string;
  capabilities?: string[];
  tools: ToolDefinition[];
  description?: string;
  sensitivity_level?: SensitivityLevel;
  signature?: string;
  metadata?: Record<string, any>;
}

export interface ServerResponse {
  server_id: string;
  status: string;
  consul_id: string | null;
}

// ============================================================================
// Pagination
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
  total?: number;
}

export interface PaginationParams {
  limit?: number;
  cursor?: string;
  sort_order?: "asc" | "desc";
}

export interface ServerListParams extends PaginationParams {
  status?: string;
  sensitivity?: string;
  team_id?: string;
  owner_id?: string;
  tags?: string;
  match_all_tags?: boolean;
  search?: string;
  include_total?: boolean;
}

// ============================================================================
// Tools & Invocation
// ============================================================================

export interface ToolInvocationRequest {
  [key: string]: any; // Dynamic parameters based on tool definition
}

export interface ToolInvocationResponse {
  success: boolean;
  result: any;
  audit_id: string;
  policy_decision: "allow" | "deny";
}

export interface ToolInvocationError {
  detail: {
    decision: "deny";
    reason: string;
    audit_id: string;
  };
}

// ============================================================================
// Policies
// ============================================================================

export interface PolicyEvaluationRequest {
  user_id: string;
  action: string;
  tool: string;
  server_id?: string;
  parameters?: Record<string, any>;
}

export interface PolicyEvaluationResponse {
  decision: "allow" | "deny";
  reason: string;
  requires_approval: boolean;
  filtered_parameters: Record<string, any> | null;
  audit_id: string;
}

export interface Policy {
  id: string;
  name: string;
  package: string;
  rules: string[];
}

export interface PoliciesResponse {
  policies: Policy[];
  total: number;
}

// ============================================================================
// Audit Logs
// ============================================================================

export type EventType =
  | "tool_invocation"
  | "policy_evaluation"
  | "authentication_success"
  | "authentication_failure"
  | "server_registered"
  | "server_updated"
  | "server_deleted";

export interface AuditEvent {
  event_id: string;
  event_type: EventType;
  timestamp: string; // ISO 8601
  user_id: string; // UUID
  user_email: string;
  server_id: string | null; // UUID
  server_name: string | null;
  tool_name: string | null;
  decision: "allow" | "deny";
  parameters: Record<string, any>;
  reason: string;
  duration_ms: number | null;
}

export interface AuditEventsParams {
  limit?: number;
  offset?: number;
  user_id?: string;
  server_id?: string;
  event_type?: string;
  start_time?: string;
  end_time?: string;
  decision?: "allow" | "deny";
}

export interface AuditEventsResponse {
  events: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditMetrics {
  period: string;
  total_events: number;
  by_event_type: Record<string, number>;
  by_decision: Record<string, number>;
  top_tools: Array<{ tool_name: string; invocations: number }>;
  top_users: Array<{ user_email: string; actions: number }>;
}

// ============================================================================
// Sessions
// ============================================================================

export interface Session {
  session_id: string;
  user_id: string; // UUID
  provider: string;
  created_at: string; // ISO 8601
  expires_at: string; // ISO 8601
  last_activity: string; // ISO 8601
}

export interface SessionsResponse {
  sessions: Session[];
  total: number;
}

// ============================================================================
// API Keys
// ============================================================================

export interface ApiKey {
  id: string; // UUID
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit: number;
  created_at: string; // ISO 8601
  expires_at: string; // ISO 8601
  last_used: string | null; // ISO 8601
  revoked: boolean;
}

export interface ApiKeyCreateRequest {
  name: string;
  description?: string;
  scopes: string[];
  rate_limit?: number;
  expires_in_days?: number;
  environment?: string;
}

export interface ApiKeyCreateResponse {
  api_key: {
    id: string;
    name: string;
    key_prefix: string;
  };
  key: string;
  message: string;
}

export interface ApiKeysResponse {
  api_keys: ApiKey[];
  total: number;
}

// ============================================================================
// Bulk Operations
// ============================================================================

export interface BulkServerRegistrationRequest {
  servers: ServerRegistrationRequest[];
  fail_on_first_error?: boolean;
}

export interface BulkServerRegistrationResult {
  name: string;
  success: boolean;
  server_id?: string;
  error?: string;
}

export interface BulkServerRegistrationResponse {
  results: BulkServerRegistrationResult[];
  total: number;
  successful: number;
  failed: number;
}

// ============================================================================
// Health
// ============================================================================

export interface HealthResponse {
  status: "healthy" | "unhealthy";
  version: string;
  environment: string;
}

export interface DetailedHealthResponse {
  status: "healthy" | "unhealthy";
  overall_healthy: boolean;
  dependencies: {
    postgresql: { healthy: boolean; latency_ms: number };
    redis: { healthy: boolean; latency_ms: number };
    opa: { healthy: boolean; latency_ms: number };
  };
}

// ============================================================================
// Error Handling
// ============================================================================

export interface ApiError {
  detail: string;
  error_code?: string;
  request_id?: string;
}

export type ErrorCode =
  | "AUTH_INVALID_CREDENTIALS"
  | "AUTH_TOKEN_EXPIRED"
  | "AUTH_INSUFFICIENT_PERMISSIONS"
  | "POLICY_DENIED"
  | "RATE_LIMIT_EXCEEDED"
  | "VALIDATION_ERROR"
  | "SERVER_NOT_FOUND"
  | "TOOL_NOT_FOUND"
  | "ALREADY_EXISTS";

// ============================================================================
// HTTP Headers
// ============================================================================

export interface RateLimitHeaders {
  "X-RateLimit-Limit": number;
  "X-RateLimit-Remaining": number;
  "X-RateLimit-Reset": number;
  "Retry-After"?: number;
}
