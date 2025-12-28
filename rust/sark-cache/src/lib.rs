use pyo3::prelude::*;

pub mod error;
pub mod lru_ttl;
pub mod python;

use python::RustCache;

/// SARK Rust Cache Module
///
/// High-performance in-memory LRU+TTL cache implemented in Rust with PyO3 bindings.
/// Provides <0.5ms p95 latency and 10-50x performance improvement over Redis.
#[pymodule]
fn sark_cache(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustCache>()?;
    Ok(())
}
