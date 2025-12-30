//! Python bindings for the SARK OPA engine using PyO3.

#![allow(clippy::useless_conversion)]
#![allow(unused_imports)]
#![allow(unused_doc_comments)]
#![allow(unexpected_cfgs)]

use crate::engine::OPAEngine;
use crate::error::OPAError;
use pyo3::exceptions::{PyException, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use regorus::Value;

/// Python exception for OPA compilation errors
pyo3::create_exception!(sark_opa, OPACompilationError, PyException);

/// Python exception for OPA evaluation errors
pyo3::create_exception!(sark_opa, OPAEvaluationError, PyException);

/// Convert OPAError to Python exception
impl From<OPAError> for PyErr {
    fn from(err: OPAError) -> PyErr {
        match err {
            OPAError::CompilationError(msg) => OPACompilationError::new_err(msg),
            OPAError::EvaluationError(msg) => OPAEvaluationError::new_err(msg),
            OPAError::InvalidInput(msg) => PyValueError::new_err(msg),
            OPAError::PolicyNotFound(msg) => {
                PyValueError::new_err(format!("Policy not found: {}", msg))
            }
            OPAError::SerializationError(msg) => {
                PyValueError::new_err(format!("Serialization error: {}", msg))
            }
            OPAError::InternalError(msg) => {
                PyRuntimeError::new_err(format!("Internal error: {}", msg))
            }
        }
    }
}

/// High-performance OPA policy evaluation engine (Python interface)
///
/// This class provides a Rust-based OPA policy evaluation engine with
/// significantly better performance than HTTP-based OPA clients.
///
/// Example:
///     >>> engine = RustOPAEngine()
///     >>> policy = '''
///     ... package authz
///     ... allow {
///     ...     input.user == "admin"
///     ... }
///     ... '''
///     >>> engine.load_policy("authz", policy)
///     >>> result = engine.evaluate("data.authz.allow", {"user": "admin"})
///     >>> print(result)
///     True
#[pyclass]
pub struct RustOPAEngine {
    /// The underlying Rust OPA engine
    inner: OPAEngine,
}

#[pymethods]
impl RustOPAEngine {
    /// Create a new OPA engine instance
    ///
    /// Returns:
    ///     RustOPAEngine: A new engine ready to load and evaluate policies
    ///
    /// Raises:
    ///     RuntimeError: If the engine cannot be initialized
    #[new]
    fn new() -> PyResult<Self> {
        let inner = OPAEngine::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Ok(Self { inner })
    }

    /// Load and compile a Rego policy
    ///
    /// Policies are cached by name. Loading a policy with an existing name
    /// will override the previous policy.
    ///
    /// Args:
    ///     name (str): Unique identifier for this policy
    ///     rego (str): The Rego policy source code
    ///
    /// Raises:
    ///     OPACompilationError: If the policy cannot be compiled
    ///     ValueError: If name or rego is empty
    ///
    /// Example:
    ///     >>> engine = RustOPAEngine()
    ///     >>> policy = "package example\\nallow = true"
    ///     >>> engine.load_policy("example", policy)
    fn load_policy(&mut self, name: String, rego: String) -> PyResult<()> {
        self.inner.load_policy(name, rego)?;
        Ok(())
    }

    /// Evaluate a query against the loaded policies
    ///
    /// Args:
    ///     query (str): The OPA query to evaluate (e.g., "data.example.allow")
    ///     input_data (dict): The input data as a Python dictionary
    ///
    /// Returns:
    ///     The evaluation result (type depends on the query)
    ///
    /// Raises:
    ///     OPAEvaluationError: If evaluation fails
    ///     ValueError: If query is empty or input cannot be serialized
    ///
    /// Example:
    ///     >>> engine = RustOPAEngine()
    ///     >>> # ... load policy ...
    ///     >>> result = engine.evaluate("data.authz.allow", {"user": "admin"})
    ///     >>> print(result)
    ///     True
    fn evaluate(
        &mut self,
        py: Python,
        query: String,
        input_data: &Bound<'_, PyDict>,
    ) -> PyResult<PyObject> {
        // Convert Python dict to serde_json::Value first
        let input_json: serde_json::Value = pythonize::depythonize(input_data.as_any())?;

        // Convert serde_json::Value to regorus::Value
        let input_regorus = serde_json::from_str(&input_json.to_string())
            .map_err(|e| PyValueError::new_err(format!("Failed to convert input: {}", e)))?;

        // Evaluate using Rust engine
        let result_regorus = self.inner.evaluate(&query, input_regorus)?;

        // Convert regorus::Value back to serde_json::Value
        let result_json: serde_json::Value = serde_json::from_str(&result_regorus.to_string())
            .map_err(|e| PyValueError::new_err(format!("Failed to convert result: {}", e)))?;

        // Convert JSON Value to Python object
        let result_py = pythonize::pythonize(py, &result_json)?;

        Ok(result_py.into())
    }

    /// Clear all loaded policies
    ///
    /// This removes all policies from the engine and clears the cache.
    ///
    /// Example:
    ///     >>> engine = RustOPAEngine()
    ///     >>> # ... load policies ...
    ///     >>> engine.clear_policies()
    fn clear_policies(&mut self) -> PyResult<()> {
        self.inner.clear_policies();
        Ok(())
    }

    /// Get the list of loaded policy names
    ///
    /// Returns:
    ///     list[str]: A list of policy names currently loaded in the engine
    ///
    /// Example:
    ///     >>> engine = RustOPAEngine()
    ///     >>> engine.load_policy("policy1", "package p1\\nallow = true")
    ///     >>> engine.load_policy("policy2", "package p2\\ndeny = true")
    ///     >>> print(engine.loaded_policies())
    ///     ['policy1', 'policy2']
    fn loaded_policies(&self) -> PyResult<Vec<String>> {
        Ok(self.inner.loaded_policies())
    }

    /// Check if a policy is loaded
    ///
    /// Args:
    ///     name (str): The policy name to check
    ///
    /// Returns:
    ///     bool: True if the policy is loaded, False otherwise
    ///
    /// Example:
    ///     >>> engine = RustOPAEngine()
    ///     >>> engine.load_policy("example", "package ex\\nallow = true")
    ///     >>> print(engine.has_policy("example"))
    ///     True
    ///     >>> print(engine.has_policy("other"))
    ///     False
    fn has_policy(&self, name: String) -> PyResult<bool> {
        Ok(self.inner.has_policy(&name))
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "RustOPAEngine(policies={})",
            self.inner.loaded_policies().len()
        )
    }
}

/// Python module for SARK OPA
#[pymodule]
fn sark_opa(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustOPAEngine>()?;
    m.add(
        "OPACompilationError",
        py.get_type_bound::<OPACompilationError>(),
    )?;
    m.add(
        "OPAEvaluationError",
        py.get_type_bound::<OPAEvaluationError>(),
    )?;
    Ok(())
}
