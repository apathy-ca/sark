use std::fmt;

#[derive(Debug, Clone)]
pub enum CacheError {
    /// Cache is at capacity and eviction failed
    CapacityExceeded,
    /// Invalid TTL value provided
    InvalidTTL(String),
    /// Internal error
    Internal(String),
}

impl fmt::Display for CacheError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CacheError::CapacityExceeded => {
                write!(f, "Cache capacity exceeded and eviction failed")
            }
            CacheError::InvalidTTL(msg) => write!(f, "Invalid TTL: {}", msg),
            CacheError::Internal(msg) => write!(f, "Internal cache error: {}", msg),
        }
    }
}

impl std::error::Error for CacheError {}

pub type Result<T> = std::result::Result<T, CacheError>;
