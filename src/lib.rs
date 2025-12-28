use pyo3::prelude::*;

// Import types from subcrates
use sark_opa::python::RustOPAEngine;
use sark_cache::python::RustCache;

/// SARK Rust Extensions
///
/// This module provides high-performance Rust implementations for SARK,
/// including OPA policy evaluation and in-memory caching.
#[pymodule]
fn sark_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add OPA engine class
    m.add_class::<RustOPAEngine>()?;

    // Add Cache class
    m.add_class::<RustCache>()?;

    Ok(())
}
