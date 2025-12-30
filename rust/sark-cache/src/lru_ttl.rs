use dashmap::DashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use crate::error::{CacheError, Result};

/// Entry stored in the cache with TTL and LRU tracking
pub struct CacheEntry {
    pub value: String,
    pub expires_at: Instant,
    pub last_accessed: AtomicU64, // Nanoseconds since cache creation
}

impl CacheEntry {
    fn new(value: String, expires_at: Instant, accessed_at: u64) -> Self {
        Self {
            value,
            expires_at,
            last_accessed: AtomicU64::new(accessed_at),
        }
    }

    /// Check if entry has expired
    #[inline]
    pub fn is_expired(&self) -> bool {
        Instant::now() >= self.expires_at
    }

    /// Update last accessed time
    #[inline]
    pub fn touch(&self, now: u64) {
        self.last_accessed.store(now, Ordering::Relaxed);
    }

    /// Get last accessed time
    #[inline]
    pub fn last_accessed_at(&self) -> u64 {
        self.last_accessed.load(Ordering::Relaxed)
    }
}

/// High-performance in-memory LRU+TTL cache using DashMap for thread-safe concurrent access
pub struct LRUTTLCache {
    map: DashMap<String, CacheEntry>,
    max_size: usize,
    default_ttl: Duration,
    start_time: Instant,
}

impl LRUTTLCache {
    /// Create a new LRU+TTL cache
    ///
    /// # Arguments
    /// * `max_size` - Maximum number of entries in cache
    /// * `ttl_secs` - Default TTL in seconds for cached entries
    pub fn new(max_size: usize, ttl_secs: u64) -> Self {
        Self {
            map: DashMap::with_capacity(max_size),
            max_size,
            default_ttl: Duration::from_secs(ttl_secs),
            start_time: Instant::now(),
        }
    }

    /// Get current time relative to cache start
    #[inline]
    fn now(&self) -> u64 {
        self.start_time.elapsed().as_nanos() as u64
    }

    /// Get a value from the cache
    ///
    /// Returns None if key doesn't exist or entry has expired
    pub fn get(&self, key: &str) -> Option<String> {
        // Fast path: check if entry exists and not expired
        let entry = self.map.get(key)?;

        if entry.is_expired() {
            // Drop the reference before removing
            drop(entry);
            self.map.remove(key);
            return None;
        }

        // Update access time for LRU
        entry.touch(self.now());
        Some(entry.value.clone())
    }

    /// Set a value in the cache with optional TTL override
    ///
    /// # Arguments
    /// * `key` - Cache key
    /// * `value` - Value to store
    /// * `ttl` - Optional TTL override in seconds (uses default if None)
    pub fn set(&self, key: String, value: String, ttl: Option<u64>) -> Result<()> {
        // Calculate expiration time
        let ttl_duration = ttl.map(Duration::from_secs).unwrap_or(self.default_ttl);
        let expires_at = Instant::now() + ttl_duration;
        let now = self.now();

        // Check if we need to evict before inserting
        if self.map.len() >= self.max_size && !self.map.contains_key(&key) {
            // Try to clean up expired entries first
            let removed = self.cleanup_expired();

            // If still at capacity, evict LRU entry
            if removed == 0 && self.map.len() >= self.max_size {
                self.evict_lru()?;
            }
        }

        let entry = CacheEntry::new(value, expires_at, now);
        self.map.insert(key, entry);
        Ok(())
    }

    /// Delete a key from the cache
    ///
    /// Returns true if the key existed and was removed
    pub fn delete(&self, key: &str) -> bool {
        self.map.remove(key).is_some()
    }

    /// Clear all entries from the cache
    pub fn clear(&self) {
        self.map.clear();
    }

    /// Get the current size of the cache
    pub fn size(&self) -> usize {
        self.map.len()
    }

    /// Evict the least recently used entry
    fn evict_lru(&self) -> Result<()> {
        let mut oldest_key: Option<String> = None;
        let mut oldest_time = u64::MAX;

        // Find the least recently used entry
        for entry in self.map.iter() {
            let accessed_at = entry.value().last_accessed_at();
            if accessed_at < oldest_time {
                oldest_time = accessed_at;
                oldest_key = Some(entry.key().clone());
            }
        }

        if let Some(key) = oldest_key {
            self.map.remove(&key);
            Ok(())
        } else {
            Err(CacheError::CapacityExceeded)
        }
    }

    /// Remove all expired entries from the cache
    ///
    /// Returns the number of entries removed
    pub fn cleanup_expired(&self) -> usize {
        let mut removed = 0;

        // Collect keys to remove (to avoid holding locks during removal)
        let expired_keys: Vec<String> = self
            .map
            .iter()
            .filter_map(|entry| {
                if entry.value().is_expired() {
                    Some(entry.key().clone())
                } else {
                    None
                }
            })
            .collect();

        for key in expired_keys {
            if self.map.remove(&key).is_some() {
                removed += 1;
            }
        }

        removed
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration as StdDuration;

    #[test]
    fn test_basic_get_set() {
        let cache = LRUTTLCache::new(100, 300);

        cache
            .set("key1".to_string(), "value1".to_string(), None)
            .unwrap();
        assert_eq!(cache.get("key1"), Some("value1".to_string()));
        assert_eq!(cache.get("key2"), None);
    }

    #[test]
    fn test_ttl_expiration() {
        let cache = LRUTTLCache::new(100, 1); // 1 second default TTL

        cache
            .set("key1".to_string(), "value1".to_string(), Some(1))
            .unwrap();
        assert_eq!(cache.get("key1"), Some("value1".to_string()));

        // Wait for expiration
        thread::sleep(StdDuration::from_millis(1100));
        assert_eq!(cache.get("key1"), None);
    }

    #[test]
    fn test_lru_eviction() {
        let cache = LRUTTLCache::new(3, 300);

        cache
            .set("key1".to_string(), "value1".to_string(), None)
            .unwrap();
        thread::sleep(StdDuration::from_millis(10));
        cache
            .set("key2".to_string(), "value2".to_string(), None)
            .unwrap();
        thread::sleep(StdDuration::from_millis(10));
        cache
            .set("key3".to_string(), "value3".to_string(), None)
            .unwrap();
        thread::sleep(StdDuration::from_millis(10));

        // Cache is at capacity, adding one more should evict key1
        cache
            .set("key4".to_string(), "value4".to_string(), None)
            .unwrap();

        assert_eq!(cache.get("key1"), None);
        assert_eq!(cache.get("key2"), Some("value2".to_string()));
        assert_eq!(cache.get("key3"), Some("value3".to_string()));
        assert_eq!(cache.get("key4"), Some("value4".to_string()));
    }

    #[test]
    fn test_delete() {
        let cache = LRUTTLCache::new(100, 300);

        cache
            .set("key1".to_string(), "value1".to_string(), None)
            .unwrap();
        assert!(cache.delete("key1"));
        assert_eq!(cache.get("key1"), None);
        assert!(!cache.delete("key1")); // Second delete returns false
    }

    #[test]
    fn test_clear() {
        let cache = LRUTTLCache::new(100, 300);

        cache
            .set("key1".to_string(), "value1".to_string(), None)
            .unwrap();
        cache
            .set("key2".to_string(), "value2".to_string(), None)
            .unwrap();

        cache.clear();
        assert_eq!(cache.size(), 0);
        assert_eq!(cache.get("key1"), None);
        assert_eq!(cache.get("key2"), None);
    }

    #[test]
    fn test_cleanup_expired() {
        let cache = LRUTTLCache::new(100, 1);

        cache
            .set("key1".to_string(), "value1".to_string(), Some(1))
            .unwrap();
        cache
            .set("key2".to_string(), "value2".to_string(), Some(10))
            .unwrap();

        thread::sleep(StdDuration::from_millis(1100));
        let removed = cache.cleanup_expired();

        assert_eq!(removed, 1);
        assert_eq!(cache.get("key1"), None);
        assert_eq!(cache.get("key2"), Some("value2".to_string()));
    }

    #[test]
    fn test_concurrent_access() {
        use std::sync::Arc;

        let cache = Arc::new(LRUTTLCache::new(1000, 300));
        let mut handles = vec![];

        // Spawn 10 threads doing concurrent operations
        for i in 0..10 {
            let cache_clone = Arc::clone(&cache);
            let handle = thread::spawn(move || {
                for j in 0..100 {
                    let key = format!("key_{}_{}", i, j);
                    let value = format!("value_{}_{}", i, j);
                    cache_clone.set(key.clone(), value.clone(), None).unwrap();
                    assert_eq!(cache_clone.get(&key), Some(value));
                }
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.join().unwrap();
        }

        // Should have 1000 entries (or close to it, depending on eviction)
        assert!(cache.size() <= 1000);
    }
}
