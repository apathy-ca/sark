use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};

use crate::lru_ttl::LRUTTLCache;
use crate::error::CacheError;

/// Python wrapper for the Rust LRU+TTL cache
#[pyclass]
pub struct RustCache {
    inner: LRUTTLCache,
}

#[pymethods]
impl RustCache {
    /// Create a new cache
    ///
    /// Args:
    ///     max_size: Maximum number of entries in cache
    ///     ttl_secs: Default TTL in seconds for cached entries
    #[new]
    fn new(max_size: usize, ttl_secs: u64) -> PyResult<Self> {
        if max_size == 0 {
            return Err(PyValueError::new_err("max_size must be greater than 0"));
        }
        if ttl_secs == 0 {
            return Err(PyValueError::new_err("ttl_secs must be greater than 0"));
        }

        Ok(Self {
            inner: LRUTTLCache::new(max_size, ttl_secs),
        })
    }

    /// Get a value from the cache
    ///
    /// Args:
    ///     key: Cache key
    ///
    /// Returns:
    ///     Cached value or None if not found/expired
    fn get(&self, key: String) -> PyResult<Option<String>> {
        Ok(self.inner.get(&key))
    }

    /// Set a value in the cache
    ///
    /// Args:
    ///     key: Cache key
    ///     value: Value to store
    ///     ttl: Optional TTL override in seconds (uses default if None)
    #[pyo3(signature = (key, value, ttl=None))]
    fn set(&self, key: String, value: String, ttl: Option<u64>) -> PyResult<()> {
        self.inner
            .set(key, value, ttl)
            .map_err(|e| map_cache_error(e))
    }

    /// Delete a key from the cache
    ///
    /// Args:
    ///     key: Cache key
    ///
    /// Returns:
    ///     True if key existed and was deleted
    fn delete(&self, key: String) -> PyResult<bool> {
        Ok(self.inner.delete(&key))
    }

    /// Clear all entries from the cache
    fn clear(&self) -> PyResult<()> {
        self.inner.clear();
        Ok(())
    }

    /// Get current cache size
    ///
    /// Returns:
    ///     Number of entries in cache
    fn size(&self) -> PyResult<usize> {
        Ok(self.inner.size())
    }

    /// Manually trigger cleanup of expired entries
    ///
    /// Returns:
    ///     Number of entries removed
    fn cleanup_expired(&self) -> PyResult<usize> {
        Ok(self.inner.cleanup_expired())
    }

    fn __repr__(&self) -> String {
        format!("RustCache(size={})", self.inner.size())
    }
}

/// Map Rust cache errors to Python exceptions
fn map_cache_error(err: CacheError) -> PyErr {
    match err {
        CacheError::CapacityExceeded => {
            PyRuntimeError::new_err("Cache capacity exceeded")
        }
        CacheError::InvalidTTL(msg) => {
            PyValueError::new_err(format!("Invalid TTL: {}", msg))
        }
        CacheError::Internal(msg) => {
            PyRuntimeError::new_err(format!("Internal cache error: {}", msg))
        }
    }
}
