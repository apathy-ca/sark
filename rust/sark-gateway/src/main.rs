//! SARK Gateway - High-Performance Authorization Service
//!
//! This binary handles the hot path for SARK:
//! - /gateway/authorize - Policy evaluation for MCP requests
//! - /gateway/authorize-a2a - Agent-to-agent authorization
//!
//! Cold path (admin, UI, complex logic) stays in Python/FastAPI.
//!
//! Architecture:
//! ```text
//! User Request → SARK Gateway (Rust) → OPA (Rust) → Cache (Rust)
//!                      ↓
//!              SARK API (Python) ← Admin/UI requests
//! ```

use anyhow::{Context, Result};
use axum::{
    extract::State,
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use clap::Parser;
use grid_cache::LRUTTLCache;
use grid_opa::OPAEngine;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::{error, info};
use tracing_subscriber;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Configuration file path
    #[arg(short, long, default_value = "/etc/sark/gateway.conf")]
    config: PathBuf,

    /// Listen address
    #[arg(short, long, default_value = "0.0.0.0:8080")]
    listen: SocketAddr,

    /// Log level (trace, debug, info, warn, error)
    #[arg(short = 'v', long, default_value = "info")]
    log_level: String,
}

/// Shared application state
#[derive(Clone)]
struct AppState {
    opa_engine: Arc<Mutex<OPAEngine>>,
    cache: Arc<LRUTTLCache>,
}

/// Gateway authorization request
#[derive(Debug, Deserialize)]
struct GatewayAuthRequest {
    action: String,
    server_name: String,
    tool_name: String,
    parameters: Option<serde_json::Value>,
    context: Option<serde_json::Value>,
    sensitivity_level: Option<String>,
}

/// Gateway authorization response
#[derive(Debug, Serialize, Deserialize)]
struct GatewayAuthResponse {
    allow: bool,
    reason: String,
    filtered_parameters: Option<serde_json::Value>,
    cache_ttl: u32,
}

/// User context extracted from JWT
#[derive(Debug, Deserialize)]
struct UserContext {
    user_id: String,
    email: String,
    roles: Vec<String>,
    permissions: Vec<String>,
}

/// Health check endpoint
async fn health() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "healthy",
        "service": "sark-gateway",
        "version": env!("CARGO_PKG_VERSION"),
        "implementation": "rust"
    }))
}

/// Gateway authorization endpoint (HOT PATH)
async fn authorize(
    State(state): State<AppState>,
    Json(request): Json<GatewayAuthRequest>,
) -> Result<Json<GatewayAuthResponse>, (StatusCode, String)> {
    info!(
        action = %request.action,
        server = %request.server_name,
        tool = %request.tool_name,
        "Gateway authorization request"
    );

    // TODO: Extract user context from JWT token (passed in Authorization header)
    // For now, placeholder
    let user = UserContext {
        user_id: "user123".to_string(),
        email: "user@example.com".to_string(),
        roles: vec!["developer".to_string()],
        permissions: vec!["mcp:invoke".to_string()],
    };

    // Build cache key
    let cache_key = format!(
        "auth:{}:{}:{}",
        user.user_id, request.action, request.server_name
    );

    // Try cache first
    if let Some(cached) = state.cache.get(&cache_key) {
        info!(cache_key = %cache_key, "Cache hit");
        if let Ok(response) = serde_json::from_str::<GatewayAuthResponse>(&cached) {
            return Ok(Json(response));
        }
    }

    // Build OPA input as regorus Value via JSON round-trip
    let opa_input_json = serde_json::json!({
        "user": {
            "id": user.user_id,
            "email": user.email,
            "roles": user.roles,
            "permissions": user.permissions,
        },
        "action": request.action,
        "resource": {
            "server": request.server_name,
            "tool": request.tool_name,
            "sensitivity": request.sensitivity_level.unwrap_or_else(|| "medium".to_string()),
        },
        "parameters": request.parameters,
        "context": request.context,
    });

    let opa_input = match grid_opa::Value::from_json_str(&opa_input_json.to_string()) {
        Ok(v) => v,
        Err(e) => {
            error!(error = %e, "Failed to build OPA input");
            return Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Failed to build OPA input: {}", e),
            ));
        }
    };

    // Evaluate policy with Rust OPA engine
    let result = {
        let mut engine = state.opa_engine.lock().await;
        engine.evaluate("data.mcp.gateway.allow", opa_input)
    };

    match result {
        Ok(value) => {
            // Extract allow bool from regorus Value — stub: treat Bool(true) as allow
            let allow = matches!(value, grid_opa::Value::Bool(true));
            let reason = if allow {
                "Policy evaluated: allowed".to_string()
            } else {
                "Policy evaluated: denied".to_string()
            };

            let response = GatewayAuthResponse {
                allow,
                reason: reason.clone(),
                filtered_parameters: None,
                cache_ttl: 300,
            };

            // Cache the decision
            if let Ok(cached_value) = serde_json::to_string(&response) {
                if let Err(e) = state.cache.set(cache_key.clone(), cached_value, Some(300)) {
                    error!(error = %e, "Failed to cache authorization decision");
                }
            }

            info!(allow = allow, reason = %reason, "Authorization decision");
            Ok(Json(response))
        }
        Err(e) => {
            error!(error = %e, "Policy evaluation failed");
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Policy evaluation error: {}", e),
            ))
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(&args.log_level)
        .init();

    info!(
        version = env!("CARGO_PKG_VERSION"),
        listen = %args.listen,
        "Starting SARK Gateway (Rust hot path)"
    );

    // Initialize OPA engine
    // TODO: Load policies from config
    let opa_engine = Arc::new(Mutex::new(
        OPAEngine::new().context("Failed to initialize OPA engine")?,
    ));

    // Initialize cache: 10K entries, 5-minute default TTL
    let cache = Arc::new(LRUTTLCache::new(10_000, 300));

    let state = AppState { opa_engine, cache };

    // Build router
    let app = Router::new()
        .route("/health", get(health))
        .route("/gateway/authorize", post(authorize))
        .with_state(state);

    // Start server
    info!("Listening on {}", args.listen);
    let listener = tokio::net::TcpListener::bind(args.listen).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
