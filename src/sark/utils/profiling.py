"""Performance profiling utilities for SARK.

This module provides utilities for profiling application performance including:
- cProfile integration for function-level profiling
- py-spy sampling profiler integration
- SQL query profiling
- Connection pool monitoring
- Cache hit rate analysis
"""

import cProfile
import io
import pstats
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = structlog.get_logger(__name__)


# ============================================================================
# FUNCTION PROFILING
# ============================================================================


class FunctionProfiler:
    """Profile function execution time and calls."""

    def __init__(self):
        """Initialize profiler."""
        self.profiles: Dict[str, pstats.Stats] = {}
        self.enabled = False

    def profile(self, func: Callable) -> Callable:
        """Decorator to profile a function.

        Args:
            func: Function to profile

        Returns:
            Wrapped function with profiling
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)

            profiler = cProfile.Profile()
            profiler.enable()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()

                # Store stats
                stats_stream = io.StringIO()
                stats = pstats.Stats(profiler, stream=stats_stream)
                stats.sort_stats("cumulative")

                func_name = f"{func.__module__}.{func.__name__}"
                if func_name in self.profiles:
                    # Merge with existing stats
                    self.profiles[func_name].add(stats)
                else:
                    self.profiles[func_name] = stats

        return wrapper

    def enable(self):
        """Enable profiling."""
        self.enabled = True

    def disable(self):
        """Disable profiling."""
        self.enabled = False

    def get_stats(self, func_name: str, limit: int = 20) -> str:
        """Get profiling statistics for a function.

        Args:
            func_name: Name of the function
            limit: Number of lines to return

        Returns:
            Formatted statistics string
        """
        if func_name not in self.profiles:
            return f"No profile data for {func_name}"

        stats_stream = io.StringIO()
        self.profiles[func_name].stream = stats_stream
        self.profiles[func_name].print_stats(limit)

        return stats_stream.getvalue()

    def reset(self):
        """Reset all profiling data."""
        self.profiles.clear()


# Global profiler instance
function_profiler = FunctionProfiler()


# ============================================================================
# SQL QUERY PROFILING
# ============================================================================


class QueryProfiler:
    """Profile SQL queries for performance analysis."""

    def __init__(self):
        """Initialize query profiler."""
        self.queries: List[Dict[str, Any]] = []
        self.enabled = False
        self.slow_query_threshold = 0.1  # 100ms

    def enable(self):
        """Enable query profiling."""
        self.enabled = True

    def disable(self):
        """Disable query profiling."""
        self.enabled = False

    def record_query(
        self,
        statement: str,
        parameters: Any,
        duration: float,
        context: Optional[str] = None,
    ):
        """Record a query execution.

        Args:
            statement: SQL statement
            parameters: Query parameters
            duration: Execution time in seconds
            context: Optional context information
        """
        if not self.enabled:
            return

        self.queries.append(
            {
                "statement": statement,
                "parameters": parameters,
                "duration": duration,
                "context": context,
                "timestamp": time.time(),
                "is_slow": duration >= self.slow_query_threshold,
            }
        )

    def get_slow_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get slow queries.

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of slow queries
        """
        slow_queries = [q for q in self.queries if q["is_slow"]]
        slow_queries.sort(key=lambda x: x["duration"], reverse=True)
        return slow_queries[:limit]

    def get_query_stats(self) -> Dict[str, Any]:
        """Get query statistics.

        Returns:
            Dictionary with query statistics
        """
        if not self.queries:
            return {
                "total_queries": 0,
                "avg_duration": 0,
                "max_duration": 0,
                "slow_queries": 0,
            }

        durations = [q["duration"] for q in self.queries]
        return {
            "total_queries": len(self.queries),
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations),
            "slow_queries": len([q for q in self.queries if q["is_slow"]]),
            "slow_query_threshold": self.slow_query_threshold,
        }

    def detect_n_plus_one(self) -> List[Dict[str, Any]]:
        """Detect potential N+1 query problems.

        Returns:
            List of potential N+1 patterns
        """
        # Group queries by statement pattern
        patterns: Dict[str, List[Dict[str, Any]]] = {}

        for query in self.queries:
            # Normalize statement (remove parameter values)
            normalized = self._normalize_statement(query["statement"])

            if normalized not in patterns:
                patterns[normalized] = []
            patterns[normalized].append(query)

        # Find patterns with high repetition
        n_plus_one_candidates = []
        for pattern, queries in patterns.items():
            if len(queries) > 10:  # Same query executed >10 times
                # Check if they happened close together
                timestamps = [q["timestamp"] for q in queries]
                time_span = max(timestamps) - min(timestamps)

                if time_span < 1.0:  # Within 1 second
                    n_plus_one_candidates.append(
                        {
                            "pattern": pattern,
                            "count": len(queries),
                            "time_span": time_span,
                            "total_duration": sum(q["duration"] for q in queries),
                            "example_query": queries[0]["statement"],
                        }
                    )

        return sorted(n_plus_one_candidates, key=lambda x: x["count"], reverse=True)

    def _normalize_statement(self, statement: str) -> str:
        """Normalize SQL statement for pattern matching.

        Args:
            statement: SQL statement

        Returns:
            Normalized statement
        """
        import re

        # Remove parameter placeholders and values
        normalized = re.sub(r"\$\d+", "?", statement)
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r"\d+", "?", normalized)

        return normalized.strip()

    def reset(self):
        """Reset query profiling data."""
        self.queries.clear()


# Global query profiler instance
query_profiler = QueryProfiler()


# Setup SQLAlchemy event listeners
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query start time."""
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query execution time."""
    total_time = time.time() - conn.info["query_start_time"].pop(-1)
    query_profiler.record_query(statement, parameters, total_time)


# ============================================================================
# CONNECTION POOL MONITORING
# ============================================================================


class ConnectionPoolMonitor:
    """Monitor database connection pool utilization."""

    def __init__(self, pool):
        """Initialize monitor.

        Args:
            pool: SQLAlchemy connection pool
        """
        self.pool = pool
        self.samples: List[Dict[str, Any]] = []

    def sample(self):
        """Take a sample of pool statistics."""
        sample = {
            "timestamp": time.time(),
            "size": self.pool.size(),
            "checked_in": self.pool.checkedin(),
            "checked_out": self.pool.checkedout(),
            "overflow": self.pool.overflow(),
            "max_overflow": self.pool._max_overflow if hasattr(self.pool, "_max_overflow") else None,
        }

        self.samples.append(sample)
        return sample

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        if not self.samples:
            return {}

        sizes = [s["size"] for s in self.samples]
        checked_out = [s["checked_out"] for s in self.samples]
        overflow = [s["overflow"] for s in self.samples]

        return {
            "samples": len(self.samples),
            "avg_size": sum(sizes) / len(sizes),
            "max_size": max(sizes),
            "avg_checked_out": sum(checked_out) / len(checked_out),
            "max_checked_out": max(checked_out),
            "avg_overflow": sum(overflow) / len(overflow),
            "max_overflow": max(overflow),
            "pool_exhaustion_count": len([s for s in self.samples if s["overflow"] > 0]),
        }


# ============================================================================
# CACHE HIT RATE ANALYSIS
# ============================================================================


class CacheAnalyzer:
    """Analyze cache hit rates and performance."""

    def __init__(self):
        """Initialize analyzer."""
        self.cache_operations: List[Dict[str, Any]] = []

    def record_operation(
        self,
        cache_key: str,
        operation: str,
        hit: bool,
        duration: Optional[float] = None,
    ):
        """Record a cache operation.

        Args:
            cache_key: Cache key
            operation: Operation type (get, set, delete)
            hit: Whether the operation was a cache hit
            duration: Operation duration in seconds
        """
        self.cache_operations.append(
            {
                "cache_key": cache_key,
                "operation": operation,
                "hit": hit,
                "duration": duration,
                "timestamp": time.time(),
            }
        )

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate percentage (0-100)
        """
        get_ops = [op for op in self.cache_operations if op["operation"] == "get"]

        if not get_ops:
            return 0.0

        hits = len([op for op in get_ops if op["hit"]])
        return (hits / len(get_ops)) * 100

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        get_ops = [op for op in self.cache_operations if op["operation"] == "get"]
        set_ops = [op for op in self.cache_operations if op["operation"] == "set"]

        if not get_ops:
            return {
                "total_operations": len(self.cache_operations),
                "hit_rate": 0,
            }

        hits = [op for op in get_ops if op["hit"]]
        misses = [op for op in get_ops if not op["hit"]]

        hit_durations = [op["duration"] for op in hits if op["duration"] is not None]
        miss_durations = [op["duration"] for op in misses if op["duration"] is not None]

        return {
            "total_operations": len(self.cache_operations),
            "get_operations": len(get_ops),
            "set_operations": len(set_ops),
            "hits": len(hits),
            "misses": len(misses),
            "hit_rate": self.get_hit_rate(),
            "avg_hit_duration": (
                sum(hit_durations) / len(hit_durations) if hit_durations else 0
            ),
            "avg_miss_duration": (
                sum(miss_durations) / len(miss_durations) if miss_durations else 0
            ),
        }

    def get_key_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Analyze cache key patterns.

        Returns:
            Dictionary with pattern statistics
        """
        patterns: Dict[str, List[Dict[str, Any]]] = {}

        for op in self.cache_operations:
            # Extract pattern (e.g., "policy:user:*")
            parts = op["cache_key"].split(":")
            if len(parts) >= 2:
                pattern = f"{parts[0]}:{parts[1]}:*"
            else:
                pattern = "other"

            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(op)

        # Calculate stats for each pattern
        pattern_stats = {}
        for pattern, ops in patterns.items():
            get_ops = [op for op in ops if op["operation"] == "get"]
            if get_ops:
                hits = len([op for op in get_ops if op["hit"]])
                pattern_stats[pattern] = {
                    "total_operations": len(ops),
                    "get_operations": len(get_ops),
                    "hits": hits,
                    "misses": len(get_ops) - hits,
                    "hit_rate": (hits / len(get_ops)) * 100,
                }

        return pattern_stats


# Global cache analyzer instance
cache_analyzer = CacheAnalyzer()


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================


@contextmanager
def profile_block(name: str):
    """Context manager for profiling a code block.

    Args:
        name: Name for the profiled block
    """
    profiler = cProfile.Profile()
    start_time = time.time()

    profiler.enable()
    try:
        yield
    finally:
        profiler.disable()
        duration = time.time() - start_time

        # Log results
        stats_stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stats_stream)
        stats.sort_stats("cumulative")
        stats.print_stats(10)

        logger.info(
            "profile_block_complete",
            name=name,
            duration=duration,
            top_functions=stats_stream.getvalue(),
        )


# ============================================================================
# REPORT GENERATION
# ============================================================================


def generate_performance_report() -> Dict[str, Any]:
    """Generate comprehensive performance report.

    Returns:
        Dictionary with performance metrics
    """
    return {
        "query_stats": query_profiler.get_query_stats(),
        "slow_queries": query_profiler.get_slow_queries(limit=10),
        "n_plus_one_candidates": query_profiler.detect_n_plus_one(),
        "cache_stats": cache_analyzer.get_stats(),
        "cache_key_patterns": cache_analyzer.get_key_patterns(),
        "function_profiles": list(function_profiler.profiles.keys()),
    }


def print_performance_report():
    """Print formatted performance report."""
    report = generate_performance_report()

    print("\n" + "=" * 60)
    print("PERFORMANCE PROFILING REPORT")
    print("=" * 60)

    # Query statistics
    print("\nQUERY STATISTICS:")
    print("-" * 60)
    query_stats = report["query_stats"]
    if query_stats["total_queries"] > 0:
        print(f"Total Queries: {query_stats['total_queries']}")
        print(f"Avg Duration: {query_stats['avg_duration']*1000:.2f}ms")
        print(f"Max Duration: {query_stats['max_duration']*1000:.2f}ms")
        print(f"Slow Queries: {query_stats['slow_queries']}")

        # Slow queries
        if report["slow_queries"]:
            print("\nTOP SLOW QUERIES:")
            for i, query in enumerate(report["slow_queries"][:5], 1):
                print(f"\n{i}. Duration: {query['duration']*1000:.2f}ms")
                print(f"   {query['statement'][:200]}")

    # N+1 detection
    if report["n_plus_one_candidates"]:
        print("\nPOTENTIAL N+1 PROBLEMS:")
        print("-" * 60)
        for candidate in report["n_plus_one_candidates"][:3]:
            print(f"\nPattern: {candidate['pattern'][:100]}")
            print(f"Executions: {candidate['count']} times in {candidate['time_span']:.2f}s")
            print(f"Total Duration: {candidate['total_duration']*1000:.2f}ms")

    # Cache statistics
    print("\nCACHE STATISTICS:")
    print("-" * 60)
    cache_stats = report["cache_stats"]
    if cache_stats.get("total_operations", 0) > 0:
        print(f"Total Operations: {cache_stats['total_operations']}")
        print(f"Hit Rate: {cache_stats['hit_rate']:.2f}%")
        print(f"Avg Hit Duration: {cache_stats['avg_hit_duration']*1000:.2f}ms")
        print(f"Avg Miss Duration: {cache_stats['avg_miss_duration']*1000:.2f}ms")

        # Key patterns
        if report["cache_key_patterns"]:
            print("\nCACHE KEY PATTERNS:")
            for pattern, stats in report["cache_key_patterns"].items():
                print(f"\n  {pattern}")
                print(f"    Hit Rate: {stats['hit_rate']:.2f}%")
                print(f"    Operations: {stats['total_operations']}")

    print("\n" + "=" * 60)
