/**
 * SARK API Client
 * Centralized HTTP client for all API interactions
 */

import axios from "axios";
import type { AxiosInstance, AxiosError, AxiosRequestConfig } from "axios";
import type {
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  LogoutRequest,
  LogoutResponse,
  User,
  Server,
  ServerListItem,
  ServerListParams,
  ServerRegistrationRequest,
  ServerResponse,
  PaginatedResponse,
  Tool,
  ToolInvocationRequest,
  ToolInvocationResponse,
  PolicyEvaluationRequest,
  PolicyEvaluationResponse,
  Policy,
  PoliciesResponse,
  AuditEventsParams,
  AuditEventsResponse,
  AuditMetrics,
  Session,
  SessionsResponse,
  ApiKey,
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
  ApiKeysResponse,
  BulkServerRegistrationRequest,
  BulkServerRegistrationResponse,
  HealthResponse,
  DetailedHealthResponse,
  ApiError,
} from "../types/api";

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

// ============================================================================
// Token Management
// ============================================================================

let accessToken: string | null = null;
let refreshToken: string | null = null;

export const setTokens = (access: string, refresh: string) => {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
};

export const getAccessToken = (): string | null => {
  if (!accessToken) {
    accessToken = localStorage.getItem("access_token");
  }
  return accessToken;
};

export const getRefreshToken = (): string | null => {
  if (!refreshToken) {
    refreshToken = localStorage.getItem("refresh_token");
  }
  return refreshToken;
};

export const clearTokens = () => {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};

// ============================================================================
// Axios Instance
// ============================================================================

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // If 401 and we haven't retried yet, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refresh = getRefreshToken();
      if (refresh) {
        try {
          const { data } = await axios.post<RefreshTokenResponse>(
            `${API_BASE_URL}${API_PREFIX}/auth/refresh`,
            { refresh_token: refresh }
          );

          setTokens(data.access_token, data.refresh_token);

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          clearTokens();
          window.location.href = "/login";
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);

// ============================================================================
// Authentication API
// ============================================================================

export const authApi = {
  /**
   * Login with LDAP credentials
   */
  loginLdap: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>(`${API_PREFIX}/auth/login/ldap`, data);
    setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  /**
   * Refresh access token
   */
  refreshToken: async (data: RefreshTokenRequest): Promise<RefreshTokenResponse> => {
    const response = await api.post<RefreshTokenResponse>(`${API_PREFIX}/auth/refresh`, data);
    setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  /**
   * Logout and invalidate tokens
   */
  logout: async (data: LogoutRequest): Promise<LogoutResponse> => {
    const response = await api.post<LogoutResponse>(`${API_PREFIX}/auth/logout`, data);
    clearTokens();
    return response.data;
  },

  /**
   * Get current authenticated user info
   */
  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>(`${API_PREFIX}/auth/me`);
    return response.data;
  },
};

// ============================================================================
// Servers API
// ============================================================================

export const serversApi = {
  /**
   * List all MCP servers with pagination and filtering
   */
  list: async (params?: ServerListParams): Promise<PaginatedResponse<ServerListItem>> => {
    const response = await api.get<PaginatedResponse<ServerListItem>>(`${API_PREFIX}/servers`, {
      params,
    });
    return response.data;
  },

  /**
   * Get server details by ID
   */
  get: async (serverId: string): Promise<Server> => {
    const response = await api.get<Server>(`${API_PREFIX}/servers/${serverId}`);
    return response.data;
  },

  /**
   * Register a new MCP server
   */
  create: async (data: ServerRegistrationRequest): Promise<ServerResponse> => {
    const response = await api.post<ServerResponse>(`${API_PREFIX}/servers`, data);
    return response.data;
  },

  /**
   * Update an existing server (full update)
   */
  update: async (serverId: string, data: ServerRegistrationRequest): Promise<ServerResponse> => {
    const response = await api.put<ServerResponse>(`${API_PREFIX}/servers/${serverId}`, data);
    return response.data;
  },

  /**
   * Partially update a server
   */
  patch: async (serverId: string, data: Partial<ServerRegistrationRequest>): Promise<ServerResponse> => {
    const response = await api.patch<ServerResponse>(`${API_PREFIX}/servers/${serverId}`, data);
    return response.data;
  },

  /**
   * Delete/deregister a server
   */
  delete: async (serverId: string): Promise<void> => {
    await api.delete(`${API_PREFIX}/servers/${serverId}`);
  },
};

// ============================================================================
// Tools API
// ============================================================================

export const toolsApi = {
  /**
   * List all tools for a server
   */
  list: async (serverId: string): Promise<Tool[]> => {
    const response = await api.get<{ tools: Tool[] }>(`${API_PREFIX}/servers/${serverId}/tools`);
    return response.data.tools;
  },

  /**
   * Get tool details
   */
  get: async (serverId: string, toolName: string): Promise<Tool> => {
    const response = await api.get<Tool>(`${API_PREFIX}/servers/${serverId}/tools/${toolName}`);
    return response.data;
  },

  /**
   * Invoke a tool
   */
  invoke: async (
    serverId: string,
    toolName: string,
    parameters: ToolInvocationRequest
  ): Promise<ToolInvocationResponse> => {
    const response = await api.post<ToolInvocationResponse>(
      `${API_PREFIX}/servers/${serverId}/tools/${toolName}/invoke`,
      parameters
    );
    return response.data;
  },
};

// ============================================================================
// Policy API
// ============================================================================

export const policyApi = {
  /**
   * Evaluate a policy decision (dry run)
   */
  evaluate: async (data: PolicyEvaluationRequest): Promise<PolicyEvaluationResponse> => {
    const response = await api.post<PolicyEvaluationResponse>(`${API_PREFIX}/policy/evaluate`, data);
    return response.data;
  },

  /**
   * List all policies
   */
  list: async (): Promise<Policy[]> => {
    const response = await api.get<PoliciesResponse>(`${API_PREFIX}/policies`);
    return response.data.policies;
  },

  /**
   * Get a specific policy
   */
  get: async (policyId: string): Promise<Policy> => {
    const response = await api.get<Policy>(`${API_PREFIX}/policies/${policyId}`);
    return response.data;
  },

  /**
   * Upload a new policy
   */
  create: async (data: { id: string; content: string }): Promise<Policy> => {
    const response = await api.post<Policy>(`${API_PREFIX}/policies`, data);
    return response.data;
  },

  /**
   * Update a policy
   */
  update: async (policyId: string, data: { content: string }): Promise<Policy> => {
    const response = await api.put<Policy>(`${API_PREFIX}/policies/${policyId}`, data);
    return response.data;
  },

  /**
   * Delete a policy
   */
  delete: async (policyId: string): Promise<void> => {
    await api.delete(`${API_PREFIX}/policies/${policyId}`);
  },
};

// ============================================================================
// Audit API
// ============================================================================

export const auditApi = {
  /**
   * Query audit events
   */
  getEvents: async (params?: AuditEventsParams): Promise<AuditEventsResponse> => {
    const response = await api.get<AuditEventsResponse>(`${API_PREFIX}/audit/events`, { params });
    return response.data;
  },

  /**
   * Get aggregated audit metrics
   */
  getMetrics: async (period: string): Promise<AuditMetrics> => {
    const response = await api.get<AuditMetrics>(`${API_PREFIX}/audit/metrics`, {
      params: { period },
    });
    return response.data;
  },
};

// ============================================================================
// Sessions API
// ============================================================================

export const sessionsApi = {
  /**
   * List active sessions
   */
  list: async (): Promise<Session[]> => {
    const response = await api.get<SessionsResponse>(`${API_PREFIX}/sessions`);
    return response.data.sessions;
  },
};

// ============================================================================
// API Keys API
// ============================================================================

export const apiKeysApi = {
  /**
   * List all API keys
   */
  list: async (includeRevoked = false): Promise<ApiKey[]> => {
    const response = await api.get<ApiKeysResponse>(`/api/auth/api-keys`, {
      params: { include_revoked: includeRevoked },
    });
    return response.data.api_keys;
  },

  /**
   * Create a new API key
   */
  create: async (data: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> => {
    const response = await api.post<ApiKeyCreateResponse>(`/api/auth/api-keys`, data);
    return response.data;
  },

  /**
   * Rotate an API key
   */
  rotate: async (keyId: string): Promise<ApiKeyCreateResponse> => {
    const response = await api.post<ApiKeyCreateResponse>(`/api/auth/api-keys/${keyId}/rotate`);
    return response.data;
  },

  /**
   * Revoke an API key
   */
  revoke: async (keyId: string): Promise<void> => {
    await api.delete(`/api/auth/api-keys/${keyId}`);
  },
};

// ============================================================================
// Bulk Operations API
// ============================================================================

export const bulkApi = {
  /**
   * Bulk register servers
   */
  registerServers: async (
    data: BulkServerRegistrationRequest
  ): Promise<BulkServerRegistrationResponse> => {
    const response = await api.post<BulkServerRegistrationResponse>(
      `${API_PREFIX}/bulk/servers/register`,
      data
    );
    return response.data;
  },
};

// ============================================================================
// Health API
// ============================================================================

export const healthApi = {
  /**
   * Basic health check
   */
  check: async (): Promise<HealthResponse> => {
    const response = await api.get<HealthResponse>(`/health`);
    return response.data;
  },

  /**
   * Detailed health check with dependencies
   */
  detailed: async (): Promise<DetailedHealthResponse> => {
    const response = await api.get<DetailedHealthResponse>(`/health/detailed`);
    return response.data;
  },
};

// ============================================================================
// Export default API client
// ============================================================================

export default api;
