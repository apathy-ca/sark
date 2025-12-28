use pyo3::prelude::*;

/// SARK Rust Extensions
///
/// This module provides high-performance Rust implementations for SARK.
#[pymodule]
fn sark_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add OPA functions
    sark_opa::register_module(m)?;

    // Add Cache functions
    sark_cache::register_module(m)?;

    Ok(())
}
