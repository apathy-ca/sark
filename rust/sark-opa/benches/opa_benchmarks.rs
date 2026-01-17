use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use regorus::Value;
use sark_opa::engine::OPAEngine;
use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};
use std::thread;

// Helper functions to create test data
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

/// Benchmark simple RBAC policy evaluation
fn bench_simple_policy(c: &mut Criterion) {
    let mut group = c.benchmark_group("opa_simple_policy");

    let mut engine = OPAEngine::new().unwrap();

    let simple_policy = r#"
        package authz

        default allow = false

        allow {
            input.role == "admin"
        }

        allow {
            input.role == "editor"
            input.action == "read"
        }
    "#;

    engine
        .load_policy("authz".to_string(), simple_policy.to_string())
        .unwrap();

    let input = value_object(vec![
        ("role", value_from_str("admin")),
        ("action", value_from_str("write")),
    ]);

    group.throughput(Throughput::Elements(1));
    group.bench_function("evaluate_simple", |b| {
        let mut engine = engine;
        b.iter(|| black_box(engine.evaluate("data.authz.allow", input.clone()).unwrap()))
    });

    group.finish();
}

/// Benchmark complex multi-tenant policy evaluation
fn bench_complex_policy(c: &mut Criterion) {
    let mut group = c.benchmark_group("opa_complex_policy");

    let mut engine = OPAEngine::new().unwrap();

    let complex_policy = r#"
        package authz

        default allow = false

        # Admin has full access
        allow {
            input.role == "admin"
        }

        # Users can read their own resources
        allow {
            input.action == "read"
            input.user_id == input.resource_owner
        }

        # Team members can read team resources
        allow {
            input.action == "read"
            input.team_id == input.resource_team
            input.role != "guest"
        }

        # Editors can write to their team's resources
        allow {
            input.action == "write"
            input.role == "editor"
            input.team_id == input.resource_team
            input.clearance_level >= 3
        }

        # Deny if sensitivity is high and clearance is low
        deny {
            input.resource_sensitivity == "high"
            input.clearance_level < 4
        }

        # Final decision considers both allow and deny
        decision = allow {
            allow
            not deny
        }
    "#;

    engine
        .load_policy("authz".to_string(), complex_policy.to_string())
        .unwrap();

    let input = value_object(vec![
        ("user_id", value_from_str("user-123")),
        ("role", value_from_str("editor")),
        ("action", value_from_str("write")),
        ("team_id", value_from_str("team-alpha")),
        ("resource_owner", value_from_str("user-456")),
        ("resource_team", value_from_str("team-alpha")),
        ("resource_sensitivity", value_from_str("medium")),
        ("clearance_level", Value::from_json_str("3").unwrap()),
    ]);

    group.throughput(Throughput::Elements(1));
    group.bench_function("evaluate_complex", |b| {
        let mut engine = engine;
        b.iter(|| black_box(engine.evaluate("data.authz.decision", input.clone()).unwrap()))
    });

    group.finish();
}

/// Benchmark policy evaluation with varying complexity
fn bench_policy_complexity_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("opa_complexity_scaling");

    for rule_count in [1, 5, 10, 20].iter() {
        let mut engine = OPAEngine::new().unwrap();

        // Generate policy with N rules
        let mut policy = String::from("package authz\n\ndefault allow = false\n\n");
        for i in 0..*rule_count {
            policy.push_str(&format!(
                "allow {{\n    input.action == \"action_{}\"\n}}\n\n",
                i
            ));
        }

        engine
            .load_policy("authz".to_string(), policy)
            .unwrap();

        let input = value_object(vec![("action", value_from_str("action_5"))]);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::from_parameter(rule_count),
            rule_count,
            |b, _rule_count| {
                let mut engine = engine;
                b.iter(|| black_box(engine.evaluate("data.authz.allow", input.clone()).unwrap()))
            },
        );
    }

    group.finish();
}

/// Benchmark batch policy evaluations
fn bench_batch_evaluation(c: &mut Criterion) {
    let mut group = c.benchmark_group("opa_batch");

    let mut engine = OPAEngine::new().unwrap();

    let policy = r#"
        package authz
        allow {
            input.role == "admin"
        }
    "#;

    engine
        .load_policy("authz".to_string(), policy.to_string())
        .unwrap();

    let inputs: Vec<Value> = (0..100)
        .map(|i| {
            value_object(vec![
                ("user_id", value_from_str(&format!("user-{}", i))),
                ("role", value_from_str(if i % 2 == 0 { "admin" } else { "user" })),
            ])
        })
        .collect();

    group.throughput(Throughput::Elements(100));
    group.bench_function("evaluate_batch_100", |b| {
        let mut engine = engine;
        b.iter(|| {
            for input in &inputs {
                black_box(engine.evaluate("data.authz.allow", input.clone()).unwrap());
            }
        })
    });

    group.finish();
}

/// Benchmark concurrent policy evaluations
fn bench_concurrent_evaluation(c: &mut Criterion) {
    let mut group = c.benchmark_group("opa_concurrent");

    for thread_count in [1, 2, 4, 8].iter() {
        let mut engine = OPAEngine::new().unwrap();

        let policy = r#"
            package authz
            allow {
                input.role == "admin"
            }
        "#;

        engine
            .load_policy("authz".to_string(), policy.to_string())
            .unwrap();

        let engine = Arc::new(Mutex::new(engine));

        group.throughput(Throughput::Elements(*thread_count as u64 * 10));
        group.bench_with_input(
            BenchmarkId::from_parameter(thread_count),
            thread_count,
            |b, &thread_count| {
                b.iter(|| {
                    let mut handles = vec![];

                    for t in 0..thread_count {
                        let engine_clone = Arc::clone(&engine);
                        let handle = thread::spawn(move || {
                            for i in 0..10 {
                                let input = value_object(vec![
                                    ("user_id", value_from_str(&format!("user-{}-{}", t, i))),
                                    ("role", value_from_str("admin")),
                                ]);

                                let mut engine = engine_clone.lock().unwrap();
                                black_box(engine.evaluate("data.authz.allow", input).unwrap());
                            }
                        });
                        handles.push(handle);
                    }

                    for handle in handles {
                        handle.join().unwrap();
                    }
                })
            },
        );
    }

    group.finish();
}

/// Benchmark policy compilation (load_policy)
fn bench_policy_compilation(c: &mut Criterion) {
    let mut group = c.benchmark_group("opa_compilation");

    let policy = r#"
        package authz

        default allow = false

        allow {
            input.role == "admin"
        }

        allow {
            input.role == "editor"
            input.action == "read"
        }
    "#;

    group.throughput(Throughput::Elements(1));
    group.bench_function("compile_policy", |b| {
        b.iter(|| {
            let mut engine = OPAEngine::new().unwrap();
            black_box(
                engine
                    .load_policy("authz".to_string(), policy.to_string())
                    .unwrap(),
            )
        })
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_simple_policy,
    bench_complex_policy,
    bench_policy_complexity_scaling,
    bench_batch_evaluation,
    bench_concurrent_evaluation,
    bench_policy_compilation
);

criterion_main!(benches);
