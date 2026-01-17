use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use sark_cache::lru_ttl::LRUTTLCache;
use std::sync::Arc;
use std::thread;

/// Benchmark single-threaded GET operations (warm cache)
fn bench_get_warm(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_get_warm");

    let cache = LRUTTLCache::new(10_000, 300);

    // Preload cache
    for i in 0..1000 {
        cache.set(
            format!("key-{}", i),
            format!("value-{}", i),
            None,
        ).unwrap();
    }

    group.throughput(Throughput::Elements(1));
    group.bench_function("get_warm", |b| {
        b.iter(|| {
            let key = format!("key-{}", black_box(500));
            black_box(cache.get(&key))
        })
    });

    group.finish();
}

/// Benchmark single-threaded SET operations
fn bench_set(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_set");

    let cache = LRUTTLCache::new(10_000, 300);
    let mut counter = 0u64;

    group.throughput(Throughput::Elements(1));
    group.bench_function("set", |b| {
        b.iter(|| {
            let key = format!("key-{}", counter);
            let value = format!("value-{}", counter);
            counter += 1;
            black_box(cache.set(key, value, None).unwrap())
        })
    });

    group.finish();
}

/// Benchmark single-threaded DELETE operations
fn bench_delete(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_delete");

    let cache = LRUTTLCache::new(10_000, 300);

    // Preload cache
    for i in 0..1000 {
        cache.set(
            format!("key-{}", i),
            format!("value-{}", i),
            None,
        ).unwrap();
    }

    let mut counter = 0u64;

    group.throughput(Throughput::Elements(1));
    group.bench_function("delete", |b| {
        b.iter(|| {
            let key = format!("key-{}", counter % 1000);
            counter += 1;
            black_box(cache.delete(&key))
        })
    });

    group.finish();
}

/// Benchmark cache MISS (cold cache)
fn bench_get_miss(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_get_miss");

    let cache = LRUTTLCache::new(10_000, 300);
    let mut counter = 0u64;

    group.throughput(Throughput::Elements(1));
    group.bench_function("get_miss", |b| {
        b.iter(|| {
            let key = format!("nonexistent-{}", counter);
            counter += 1;
            black_box(cache.get(&key))
        })
    });

    group.finish();
}

/// Benchmark concurrent reads with varying thread counts
fn bench_concurrent_reads(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_concurrent_reads");

    for thread_count in [1, 2, 4, 8, 16].iter() {
        let cache = Arc::new(LRUTTLCache::new(10_000, 300));

        // Preload cache
        for i in 0..1000 {
            cache.set(
                format!("key-{}", i),
                format!("value-{}", i),
                None,
            ).unwrap();
        }

        group.throughput(Throughput::Elements(*thread_count as u64 * 100));
        group.bench_with_input(
            BenchmarkId::from_parameter(thread_count),
            thread_count,
            |b, &thread_count| {
                b.iter(|| {
                    let mut handles = vec![];

                    for _ in 0..thread_count {
                        let cache_clone = Arc::clone(&cache);
                        let handle = thread::spawn(move || {
                            for i in 0..100 {
                                let key = format!("key-{}", i % 1000);
                                black_box(cache_clone.get(&key));
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

/// Benchmark concurrent writes with varying thread counts
fn bench_concurrent_writes(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_concurrent_writes");

    for thread_count in [1, 2, 4, 8].iter() {
        let cache = Arc::new(LRUTTLCache::new(10_000, 300));

        group.throughput(Throughput::Elements(*thread_count as u64 * 100));
        group.bench_with_input(
            BenchmarkId::from_parameter(thread_count),
            thread_count,
            |b, &thread_count| {
                let mut base_counter = 0u64;
                b.iter(|| {
                    let mut handles = vec![];

                    for t in 0..thread_count {
                        let cache_clone = Arc::clone(&cache);
                        let start = base_counter + (t as u64 * 100);
                        let handle = thread::spawn(move || {
                            for i in 0..100 {
                                let key = format!("key-{}", start + i);
                                let value = format!("value-{}", start + i);
                                cache_clone.set(key, value, None).unwrap();
                            }
                        });
                        handles.push(handle);
                    }

                    for handle in handles {
                        handle.join().unwrap();
                    }

                    base_counter += thread_count as u64 * 100;
                })
            },
        );
    }

    group.finish();
}

/// Benchmark cache scaling with different sizes
fn bench_cache_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_scaling");

    for size in [100, 1_000, 10_000, 100_000].iter() {
        let cache = LRUTTLCache::new(*size, 300);

        // Fill cache to 50% capacity
        for i in 0..(size / 2) {
            cache.set(
                format!("key-{}", i),
                format!("value-{}", i),
                None,
            ).unwrap();
        }

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::from_parameter(size),
            size,
            |b, _size| {
                b.iter(|| {
                    black_box(cache.get("key-100"))
                })
            },
        );
    }

    group.finish();
}

/// Benchmark LRU eviction performance
fn bench_eviction(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_eviction");

    let cache = LRUTTLCache::new(100, 300);

    // Fill cache to capacity
    for i in 0..100 {
        cache.set(
            format!("key-{}", i),
            format!("value-{}", i),
            None,
        ).unwrap();
    }

    let mut counter = 100u64;

    group.throughput(Throughput::Elements(1));
    group.bench_function("evict_lru", |b| {
        b.iter(|| {
            let key = format!("key-{}", counter);
            let value = format!("value-{}", counter);
            counter += 1;
            black_box(cache.set(key, value, None).unwrap())
        })
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_get_warm,
    bench_set,
    bench_delete,
    bench_get_miss,
    bench_concurrent_reads,
    bench_concurrent_writes,
    bench_cache_scaling,
    bench_eviction
);

criterion_main!(benches);
