//! Core OPA policy evaluation engine using Regorus.

use crate::error::{OPAError, Result};
use regorus::{Engine as RegorusEngine, Value};
use std::collections::HashMap;

/// High-performance OPA policy evaluation engine
///
/// This engine maintains a cache of compiled policies and uses the Regorus
/// library for fast, embedded policy evaluation without network overhead.
pub struct OPAEngine {
    /// The underlying Regorus engine
    engine: RegorusEngine,

    /// Cache of loaded policy names and their Rego source code
    policies: HashMap<String, String>,
}

impl OPAEngine {
    /// Create a new OPA engine instance
    ///
    /// # Returns
    ///
    /// A new `OPAEngine` ready to load and evaluate policies
    ///
    /// # Example
    ///
    /// ```
    /// use sark_opa::engine::OPAEngine;
    ///
    /// let engine = OPAEngine::new().unwrap();
    /// ```
    pub fn new() -> Result<Self> {
        let engine = RegorusEngine::new();

        Ok(Self {
            engine,
            policies: HashMap::new(),
        })
    }

    /// Load and compile a Rego policy
    ///
    /// Policies are cached by name. Loading a policy with an existing name
    /// will override the previous policy.
    ///
    /// # Arguments
    ///
    /// * `name` - Unique identifier for this policy
    /// * `rego` - The Rego policy source code
    ///
    /// # Returns
    ///
    /// `Ok(())` on success, or an error if the policy cannot be compiled
    ///
    /// # Example
    ///
    /// ```
    /// # use sark_opa::engine::OPAEngine;
    /// let mut engine = OPAEngine::new().unwrap();
    ///
    /// let policy = r#"
    ///     package example
    ///     allow {
    ///         input.user == "admin"
    ///     }
    /// "#;
    ///
    /// engine.load_policy("example".to_string(), policy.to_string()).unwrap();
    /// ```
    pub fn load_policy(&mut self, name: String, rego: String) -> Result<()> {
        if name.is_empty() {
            return Err(OPAError::InvalidInput(
                "Policy name cannot be empty".to_string(),
            ));
        }

        if rego.is_empty() {
            return Err(OPAError::InvalidInput(
                "Policy source cannot be empty".to_string(),
            ));
        }

        // If a policy with this name already exists, we need to clear and reload
        // because Regorus doesn't support updating policies in place
        if self.policies.contains_key(&name) {
            // Clear all policies and reload them except the old version
            let old_policies: Vec<(String, String)> = self
                .policies
                .iter()
                .filter(|(k, _)| *k != &name)
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect();

            // Create new engine
            self.engine = RegorusEngine::new();
            self.policies.clear();

            // Reload all policies except the one being replaced
            for (policy_name, policy_code) in old_policies {
                self.engine
                    .add_policy(policy_name.clone(), policy_code.clone())
                    .map_err(|e| OPAError::CompilationError(e.to_string()))?;
                self.policies.insert(policy_name, policy_code);
            }
        }

        // Add the new policy to Regorus engine
        self.engine
            .add_policy(name.clone(), rego.clone())
            .map_err(|e| OPAError::CompilationError(e.to_string()))?;

        // Cache the policy source
        self.policies.insert(name, rego);

        Ok(())
    }

    /// Evaluate a query against the loaded policies
    ///
    /// # Arguments
    ///
    /// * `query` - The OPA query to evaluate (e.g., "data.example.allow")
    /// * `input` - The input data as a JSON value
    ///
    /// # Returns
    ///
    /// The evaluation result as a JSON value, or an error if evaluation fails
    ///
    /// # Example
    ///
    /// ```
    /// # use sark_opa::engine::OPAEngine;
    /// # use regorus::Value;
    /// # use std::collections::BTreeMap;
    /// # use std::sync::Arc;
    /// let mut engine = OPAEngine::new().unwrap();
    ///
    /// let policy = r#"
    ///     package example
    ///     allow {
    ///         input.user == "admin"
    ///     }
    /// "#;
    ///
    /// engine.load_policy("example".to_string(), policy.to_string()).unwrap();
    ///
    /// let mut input_map = BTreeMap::new();
    /// input_map.insert(Value::String("user".into()), Value::String("admin".into()));
    /// let input = Value::Object(Arc::new(input_map));
    /// let result = engine.evaluate("data.example.allow", input).unwrap();
    /// assert_eq!(result, Value::Bool(true));
    /// ```
    pub fn evaluate(&mut self, query: &str, input: Value) -> Result<Value> {
        if query.is_empty() {
            return Err(OPAError::InvalidInput("Query cannot be empty".to_string()));
        }

        // Set the input data
        self.engine.set_input(input);

        // Evaluate the query
        let results = self
            .engine
            .eval_query(query.to_string(), false)
            .map_err(|e| OPAError::EvaluationError(e.to_string()))?;

        // Extract the result from QueryResults
        // QueryResults contains a Vec of QueryResult, each has expressions
        if let Some(query_result) = results.result.first() {
            // Get the first expression from the QueryResult
            if let Some(expr) = query_result.expressions.first() {
                Ok(expr.value.clone())
            } else {
                // No expressions means undefined result
                Ok(Value::Bool(false))
            }
        } else {
            // No results means the query didn't match - return false for boolean queries
            Ok(Value::Bool(false))
        }
    }

    /// Clear all loaded policies
    ///
    /// This removes all policies from the engine and clears the cache.
    /// After calling this method, you'll need to reload policies before
    /// evaluation.
    ///
    /// # Example
    ///
    /// ```
    /// # use sark_opa::engine::OPAEngine;
    /// let mut engine = OPAEngine::new().unwrap();
    /// // ... load policies ...
    /// engine.clear_policies();
    /// ```
    pub fn clear_policies(&mut self) {
        // Create a new engine to clear all policies
        self.engine = RegorusEngine::new();
        self.policies.clear();
    }

    /// Get the list of loaded policy names
    ///
    /// # Returns
    ///
    /// A vector of policy names currently loaded in the engine
    pub fn loaded_policies(&self) -> Vec<String> {
        self.policies.keys().cloned().collect()
    }

    /// Check if a policy is loaded
    ///
    /// # Arguments
    ///
    /// * `name` - The policy name to check
    ///
    /// # Returns
    ///
    /// `true` if the policy is loaded, `false` otherwise
    pub fn has_policy(&self, name: &str) -> bool {
        self.policies.contains_key(name)
    }
}

impl Default for OPAEngine {
    fn default() -> Self {
        Self::new().expect("Failed to create default OPA engine")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;
    use std::sync::Arc;

    fn value_from_str(s: &str) -> Value {
        Value::String(s.into())
    }

    fn value_object(pairs: Vec<(&str, Value)>) -> Value {
        let mut map = BTreeMap::new();
        for (k, v) in pairs {
            map.insert(Value::String(k.into()), v);
        }
        Value::Object(Arc::new(map))
    }

    #[test]
    fn test_new_engine() {
        let engine = OPAEngine::new();
        assert!(engine.is_ok());
        assert_eq!(engine.unwrap().loaded_policies().len(), 0);
    }

    #[test]
    fn test_load_valid_policy() {
        let mut engine = OPAEngine::new().unwrap();

        let policy = r#"
            package example
            allow {
                input.user == "admin"
            }
        "#;

        let result = engine.load_policy("example".to_string(), policy.to_string());
        assert!(result.is_ok());
        assert!(engine.has_policy("example"));
        assert_eq!(engine.loaded_policies().len(), 1);
    }

    #[test]
    fn test_load_invalid_policy() {
        let mut engine = OPAEngine::new().unwrap();

        let invalid_policy = "this is not valid rego";

        let result = engine.load_policy("invalid".to_string(), invalid_policy.to_string());
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), OPAError::CompilationError(_)));
    }

    #[test]
    fn test_empty_policy_name() {
        let mut engine = OPAEngine::new().unwrap();

        let policy = "package test\nallow = true";

        let result = engine.load_policy("".to_string(), policy.to_string());
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), OPAError::InvalidInput(_)));
    }

    #[test]
    fn test_empty_policy_source() {
        let mut engine = OPAEngine::new().unwrap();

        let result = engine.load_policy("test".to_string(), "".to_string());
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), OPAError::InvalidInput(_)));
    }

    #[test]
    fn test_evaluate_simple_query() {
        let mut engine = OPAEngine::new().unwrap();

        let policy = r#"
            package example
            allow {
                input.user == "admin"
            }
        "#;

        engine
            .load_policy("example".to_string(), policy.to_string())
            .unwrap();

        let input = value_object(vec![("user", value_from_str("admin"))]);
        let result = engine.evaluate("data.example.allow", input).unwrap();

        assert_eq!(result, Value::Bool(true));
    }

    #[test]
    fn test_evaluate_with_missing_input() {
        let mut engine = OPAEngine::new().unwrap();

        let policy = r#"
            package example
            allow {
                input.user == "admin"
            }
        "#;

        engine
            .load_policy("example".to_string(), policy.to_string())
            .unwrap();

        let input = value_object(vec![]);
        let result = engine.evaluate("data.example.allow", input).unwrap();

        // When input.user is missing, the rule should not match
        assert_eq!(result, Value::Bool(false));
    }

    #[test]
    fn test_multiple_policies() {
        let mut engine = OPAEngine::new().unwrap();

        let policy1 = r#"
            package policy1
            allow = true
        "#;

        let policy2 = r#"
            package policy2
            deny = true
        "#;

        engine
            .load_policy("policy1".to_string(), policy1.to_string())
            .unwrap();
        engine
            .load_policy("policy2".to_string(), policy2.to_string())
            .unwrap();

        assert_eq!(engine.loaded_policies().len(), 2);
        assert!(engine.has_policy("policy1"));
        assert!(engine.has_policy("policy2"));

        let empty_input = value_object(vec![]);
        let result1 = engine
            .evaluate("data.policy1.allow", empty_input.clone())
            .unwrap();
        assert_eq!(result1, Value::Bool(true));

        let result2 = engine.evaluate("data.policy2.deny", empty_input).unwrap();
        assert_eq!(result2, Value::Bool(true));
    }

    #[test]
    fn test_policy_override() {
        let mut engine = OPAEngine::new().unwrap();

        let policy_v1 = r#"
            package example
            result = "v1"
        "#;

        let policy_v2 = r#"
            package example
            result = "v2"
        "#;

        engine
            .load_policy("example".to_string(), policy_v1.to_string())
            .unwrap();

        let empty_input = value_object(vec![]);
        let result1 = engine
            .evaluate("data.example.result", empty_input.clone())
            .unwrap();
        assert_eq!(result1, Value::String("v1".into()));

        // Override with new policy
        engine
            .load_policy("example".to_string(), policy_v2.to_string())
            .unwrap();

        let result2 = engine.evaluate("data.example.result", empty_input).unwrap();
        assert_eq!(result2, Value::String("v2".into()));
    }

    #[test]
    fn test_clear_policies() {
        let mut engine = OPAEngine::new().unwrap();

        let policy = r#"
            package example
            allow = true
        "#;

        engine
            .load_policy("example".to_string(), policy.to_string())
            .unwrap();
        assert_eq!(engine.loaded_policies().len(), 1);

        engine.clear_policies();
        assert_eq!(engine.loaded_policies().len(), 0);
        assert!(!engine.has_policy("example"));
    }

    #[test]
    fn test_empty_query() {
        let mut engine = OPAEngine::new().unwrap();

        let policy = r#"
            package example
            allow = true
        "#;

        engine
            .load_policy("example".to_string(), policy.to_string())
            .unwrap();

        let empty_input = value_object(vec![]);
        let result = engine.evaluate("", empty_input);
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), OPAError::InvalidInput(_)));
    }
}
