use pyo3::prelude::*;

// Import types from grid-core (shared Rust components)
// See ../sark-core/README.md for documentation
use grid_cache::python::RustCache;
use grid_opa::python::RustOPAEngine;

/// SARK Rust Extensions
///
/// This module provides high-performance Rust implementations for SARK,
/// including OPA policy evaluation and in-memory caching.
///
/// The underlying implementations are from grid-core, the shared Rust
/// component library used by both SARK and YORI projects.
#[pymodule]
fn sark_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add OPA engine class
    m.add_class::<RustOPAEngine>()?;

    // Add Cache class
    m.add_class::<RustCache>()?;

    Ok(())
}
