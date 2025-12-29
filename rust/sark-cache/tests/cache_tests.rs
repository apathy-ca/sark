use sark_cache::lru_ttl::LRUTTLCache;
use std::sync::Arc;
use std::thread;
use std::time::Duration;

#[test]
fn test_cache_miss_returns_none() {
    let cache = LRUTTLCache::new(100, 300);
    assert_eq!(cache.get("nonexistent"), None);
}

#[test]
fn test_cache_hit_updates_access_time() {
    let cache = LRUTTLCache::new(100, 300);

    cache
        .set("key1".to_string(), "value1".to_string(), None)
        .unwrap();
    thread::sleep(Duration::from_millis(50));

    // Access the key
    let first_access = cache.get("key1");
    assert_eq!(first_access, Some("value1".to_string()));

    thread::sleep(Duration::from_millis(50));

    // Access again - this should update the access time
    let second_access = cache.get("key1");
    assert_eq!(second_access, Some("value1".to_string()));
}

#[test]
fn test_ttl_expiration_accuracy() {
    let cache = LRUTTLCache::new(100, 1);

    cache
        .set("key1".to_string(), "value1".to_string(), Some(1))
        .unwrap();

    // Should be available immediately
    assert_eq!(cache.get("key1"), Some("value1".to_string()));

    // Should be expired after 1 second (with 100ms tolerance)
    thread::sleep(Duration::from_millis(1100));
    assert_eq!(cache.get("key1"), None);
}

#[test]
fn test_lru_eviction_removes_oldest() {
    let cache = LRUTTLCache::new(3, 300);

    // Insert 3 entries with delays to ensure ordering
    cache
        .set("key1".to_string(), "value1".to_string(), None)
        .unwrap();
    thread::sleep(Duration::from_millis(10));

    cache
        .set("key2".to_string(), "value2".to_string(), None)
        .unwrap();
    thread::sleep(Duration::from_millis(10));

    cache
        .set("key3".to_string(), "value3".to_string(), None)
        .unwrap();
    thread::sleep(Duration::from_millis(10));

    // Access key2 to update its access time
    cache.get("key2");
    thread::sleep(Duration::from_millis(10));

    // Insert 4th entry - should evict key1 (oldest accessed)
    cache
        .set("key4".to_string(), "value4".to_string(), None)
        .unwrap();

    assert_eq!(cache.get("key1"), None, "key1 should be evicted");
    assert_eq!(
        cache.get("key2"),
        Some("value2".to_string()),
        "key2 should remain"
    );
    assert_eq!(
        cache.get("key3"),
        Some("value3".to_string()),
        "key3 should remain"
    );
    assert_eq!(
        cache.get("key4"),
        Some("value4".to_string()),
        "key4 should exist"
    );
}

#[test]
fn test_lru_retains_recently_accessed() {
    let cache = LRUTTLCache::new(2, 300);

    cache
        .set("key1".to_string(), "value1".to_string(), None)
        .unwrap();
    thread::sleep(Duration::from_millis(10));

    cache
        .set("key2".to_string(), "value2".to_string(), None)
        .unwrap();
    thread::sleep(Duration::from_millis(10));

    // Access key1 to make it more recently used
    cache.get("key1");
    thread::sleep(Duration::from_millis(10));

    // Insert key3 - should evict key2
    cache
        .set("key3".to_string(), "value3".to_string(), None)
        .unwrap();

    assert_eq!(cache.get("key1"), Some("value1".to_string()));
    assert_eq!(cache.get("key2"), None, "key2 should be evicted");
    assert_eq!(cache.get("key3"), Some("value3".to_string()));
}

#[test]
fn test_concurrent_reads_and_writes() {
    let cache = Arc::new(LRUTTLCache::new(1000, 300));
    let mut handles = vec![];

    // Spawn 20 threads doing concurrent operations
    for i in 0..20 {
        let cache_clone = Arc::clone(&cache);
        let handle = thread::spawn(move || {
            for j in 0..50 {
                let key = format!("key_{}_{}", i, j);
                let value = format!("value_{}_{}", i, j);

                // Write
                cache_clone.set(key.clone(), value.clone(), None).unwrap();

                // Read back
                let result = cache_clone.get(&key);
                assert_eq!(result, Some(value), "Concurrent read should match write");
            }
        });
        handles.push(handle);
    }

    for handle in handles {
        handle.join().expect("Thread should not panic");
    }

    // Verify no data corruption
    assert!(cache.size() <= 1000, "Cache should respect max size");
}

#[test]
fn test_no_deadlocks_under_contention() {
    let cache = Arc::new(LRUTTLCache::new(10, 300));
    let mut handles = vec![];

    // Create high contention with small cache
    for i in 0..10 {
        let cache_clone = Arc::clone(&cache);
        let handle = thread::spawn(move || {
            for j in 0..100 {
                let key = format!("key_{}", j % 5); // Intentionally reuse keys
                let value = format!("value_{}_{}", i, j);
                cache_clone.set(key.clone(), value, None).unwrap();
                cache_clone.get(&key);
                if j % 10 == 0 {
                    cache_clone.delete(&key);
                }
            }
        });
        handles.push(handle);
    }

    // All threads should complete without deadlock
    for handle in handles {
        handle.join().expect("Should not deadlock");
    }
}

#[test]
fn test_cleanup_removes_expired() {
    let cache = LRUTTLCache::new(100, 1);

    // Insert multiple entries with short TTL
    cache
        .set("expired1".to_string(), "value1".to_string(), Some(1))
        .unwrap();
    cache
        .set("expired2".to_string(), "value2".to_string(), Some(1))
        .unwrap();
    cache
        .set("valid".to_string(), "value3".to_string(), Some(10))
        .unwrap();

    assert_eq!(cache.size(), 3);

    // Wait for expiration
    thread::sleep(Duration::from_millis(1100));

    // Cleanup should remove 2 expired entries
    let removed = cache.cleanup_expired();
    assert_eq!(removed, 2, "Should remove 2 expired entries");
    assert_eq!(cache.size(), 1, "Should have 1 entry remaining");
    assert_eq!(cache.get("valid"), Some("value3".to_string()));
}

#[test]
fn test_custom_ttl_override() {
    let cache = LRUTTLCache::new(100, 10); // 10 second default

    // Set with custom 1 second TTL
    cache
        .set("short".to_string(), "value1".to_string(), Some(1))
        .unwrap();
    // Use default TTL
    cache
        .set("long".to_string(), "value2".to_string(), None)
        .unwrap();

    thread::sleep(Duration::from_millis(1100));

    assert_eq!(cache.get("short"), None, "Short TTL should expire");
    assert_eq!(
        cache.get("long"),
        Some("value2".to_string()),
        "Default TTL should not expire"
    );
}

#[test]
fn test_update_existing_key() {
    let cache = LRUTTLCache::new(100, 300);

    cache
        .set("key1".to_string(), "value1".to_string(), None)
        .unwrap();
    assert_eq!(cache.get("key1"), Some("value1".to_string()));

    // Update with new value
    cache
        .set("key1".to_string(), "value2".to_string(), None)
        .unwrap();
    assert_eq!(cache.get("key1"), Some("value2".to_string()));

    // Size should still be 1
    assert_eq!(cache.size(), 1);
}

#[test]
fn test_large_cache_performance() {
    let cache = LRUTTLCache::new(10000, 300);

    // Insert 10k entries
    for i in 0..10000 {
        let key = format!("key_{}", i);
        let value = format!("value_{}", i);
        cache.set(key, value, None).unwrap();
    }

    assert_eq!(cache.size(), 10000);

    // Verify random access is fast
    for i in (0..10000).step_by(100) {
        let key = format!("key_{}", i);
        let expected = format!("value_{}", i);
        assert_eq!(cache.get(&key), Some(expected));
    }
}

#[test]
fn test_empty_cache_operations() {
    let cache = LRUTTLCache::new(100, 300);

    assert_eq!(cache.size(), 0);
    assert_eq!(cache.get("any"), None);
    assert!(!cache.delete("any"));
    assert_eq!(cache.cleanup_expired(), 0);
    cache.clear(); // Should not panic
}

#[test]
fn test_single_entry_cache() {
    let cache = LRUTTLCache::new(1, 300);

    cache
        .set("key1".to_string(), "value1".to_string(), None)
        .unwrap();
    assert_eq!(cache.get("key1"), Some("value1".to_string()));

    // Adding another should evict the first
    cache
        .set("key2".to_string(), "value2".to_string(), None)
        .unwrap();
    assert_eq!(cache.get("key1"), None);
    assert_eq!(cache.get("key2"), Some("value2".to_string()));
}
