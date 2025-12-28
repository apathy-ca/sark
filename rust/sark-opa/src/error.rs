//! Error types for the SARK OPA engine.

use std::fmt;

/// Result type for OPA engine operations
pub type Result<T> = std::result::Result<T, OPAError>;

/// Errors that can occur during OPA policy evaluation
#[derive(Debug, Clone)]
pub enum OPAError {
    /// Policy compilation failed
    CompilationError(String),

    /// Policy evaluation failed
    EvaluationError(String),

    /// Invalid policy name or query
    InvalidInput(String),

    /// Policy not found
    PolicyNotFound(String),

    /// JSON serialization/deserialization error
    SerializationError(String),

    /// Internal engine error
    InternalError(String),
}

impl fmt::Display for OPAError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            OPAError::CompilationError(msg) => write!(f, "Policy compilation failed: {}", msg),
            OPAError::EvaluationError(msg) => write!(f, "Policy evaluation failed: {}", msg),
            OPAError::InvalidInput(msg) => write!(f, "Invalid input: {}", msg),
            OPAError::PolicyNotFound(name) => write!(f, "Policy not found: {}", name),
            OPAError::SerializationError(msg) => write!(f, "Serialization error: {}", msg),
            OPAError::InternalError(msg) => write!(f, "Internal error: {}", msg),
        }
    }
}

impl std::error::Error for OPAError {}

impl From<serde_json::Error> for OPAError {
    fn from(err: serde_json::Error) -> Self {
        OPAError::SerializationError(err.to_string())
    }
}

impl From<anyhow::Error> for OPAError {
    fn from(err: anyhow::Error) -> Self {
        OPAError::InternalError(err.to_string())
    }
}
