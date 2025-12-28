use pyo3::prelude::*;

/// Hello world function to verify OPA module is working
#[pyfunction]
fn hello_opa() -> PyResult<String> {
    Ok("Hello from SARK OPA engine!".to_string())
}

/// Register the OPA module functions
///
/// Provides high-performance Open Policy Agent (OPA) policy evaluation
/// implemented in Rust with Python bindings.
///
/// This module will contain:
/// - Policy compilation and caching
/// - Fast policy evaluation using regorus
/// - Thread-safe policy storage
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello_opa, m)?)?;
    Ok(())
}
