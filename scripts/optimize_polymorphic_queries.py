#!/usr/bin/env python3
"""
SARK v2.0 Polymorphic Query Optimization Tool

This script analyzes and optimizes queries against the polymorphic v2.0 schema
(resources, capabilities) to ensure high performance across multiple protocols.

Usage:
    python scripts/optimize_polymorphic_queries.py --analyze      # Analyze current query performance
    python scripts/optimize_polymorphic_queries.py --benchmark    # Run query benchmarks
    python scripts/optimize_polymorphic_queries.py --optimize     # Apply query optimizations
    python scripts/optimize_polymorphic_queries.py --report       # Generate performance report

Key Optimizations:
1. GIN indexes on JSONB metadata columns for fast JSON queries
2. Partial indexes on protocol-specific queries
3. Covering indexes for common query patterns
4. Query plan analysis and recommendations
"""

import argparse
import sys
import logging
import json
from datetime import datetime, UTC
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class QueryBenchmark:
    """Query benchmark result."""
    query_name: str
    query: str
    execution_time_ms: float
    rows_returned: int
    plan_cost: Optional[float] = None
    uses_index: bool = False
    index_name: Optional[str] = None


@dataclass
class OptimizationRecommendation:
    """Query optimization recommendation."""
    query_pattern: str
    current_performance_ms: float
    recommendation: str
    estimated_improvement: str
    priority: str  # 'high', 'medium', 'low'


def get_database_url() -> str:
    """Get database URL from environment or default."""
    import os
    return os.getenv(
        "DATABASE_URL",
        "postgresql://sark:sark@localhost:5432/sark",
    )


def create_session() -> Session:
    """Create database session."""
    engine = create_engine(get_database_url(), echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


# ============================================================================
# Common Query Patterns
# ============================================================================

QUERY_PATTERNS = {
    # Protocol-specific queries
    "list_resources_by_protocol": """
        SELECT id, name, protocol, endpoint, sensitivity_level
        FROM resources
        WHERE protocol = :protocol
        ORDER BY name
        LIMIT 100
    """,

    # JSONB metadata queries
    "search_resources_by_metadata": """
        SELECT id, name, protocol, endpoint
        FROM resources
        WHERE metadata @> :metadata_filter
        LIMIT 100
    """,

    # JOIN queries (resource + capabilities)
    "list_capabilities_with_resources": """
        SELECT r.id, r.name, r.protocol, c.id, c.name, c.sensitivity_level
        FROM resources r
        JOIN capabilities c ON c.resource_id = r.id
        WHERE r.protocol = :protocol
        ORDER BY r.name, c.name
        LIMIT 100
    """,

    # Sensitivity filtering
    "high_sensitivity_capabilities": """
        SELECT c.id, c.name, c.sensitivity_level, r.protocol
        FROM capabilities c
        JOIN resources r ON r.id = c.resource_id
        WHERE c.sensitivity_level IN ('high', 'critical')
        ORDER BY c.sensitivity_level DESC, c.name
        LIMIT 100
    """,

    # Complex JSONB queries
    "search_capabilities_by_input_schema": """
        SELECT c.id, c.name, c.input_schema, r.protocol
        FROM capabilities c
        JOIN resources r ON r.id = c.resource_id
        WHERE c.input_schema ? :schema_key
        ORDER BY c.name
        LIMIT 100
    """,

    # Aggregation queries
    "count_capabilities_per_protocol": """
        SELECT r.protocol, COUNT(c.id) as capability_count
        FROM resources r
        LEFT JOIN capabilities c ON c.resource_id = r.id
        GROUP BY r.protocol
        ORDER BY capability_count DESC
    """,

    # Multi-protocol federated query
    "cross_protocol_capabilities": """
        SELECT r.protocol, c.name, c.sensitivity_level, c.input_schema->>'type' as input_type
        FROM capabilities c
        JOIN resources r ON r.id = c.resource_id
        WHERE r.protocol IN ('mcp', 'http', 'grpc')
          AND c.sensitivity_level != 'low'
        ORDER BY r.protocol, c.name
        LIMIT 100
    """,

    # Cost tracking join
    "resource_cost_analysis": """
        SELECT r.id, r.name, r.protocol,
               COUNT(ct.id) as invocation_count,
               SUM(ct.actual_cost) as total_cost
        FROM resources r
        JOIN capabilities c ON c.resource_id = r.id
        JOIN cost_tracking ct ON ct.capability_id = c.id
        WHERE ct.timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY r.id, r.name, r.protocol
        ORDER BY total_cost DESC
        LIMIT 50
    """,
}


def benchmark_query(session: Session, query_name: str, query: str, params: Dict) -> QueryBenchmark:
    """
    Benchmark a single query.

    Returns execution time, row count, and query plan analysis.
    """
    logger.debug(f"Benchmarking query: {query_name}")

    # Execute EXPLAIN ANALYZE to get query plan and timing
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"

    try:
        start = time.perf_counter()
        result = session.execute(text(query), params)
        rows = result.fetchall()
        end = time.perf_counter()
        execution_time_ms = (end - start) * 1000

        # Get query plan
        plan_result = session.execute(text(explain_query), params)
        plan_data = plan_result.scalar()

        if plan_data and isinstance(plan_data, list) and len(plan_data) > 0:
            plan = plan_data[0].get("Plan", {})
            plan_cost = plan.get("Total Cost", 0)

            # Check if index is used
            plan_str = json.dumps(plan)
            uses_index = "Index Scan" in plan_str or "Index Only Scan" in plan_str

            # Extract index name if used
            index_name = None
            if uses_index and "Index Name" in plan_str:
                # Simple extraction - could be improved
                index_name = plan.get("Index Name", "unknown")
        else:
            plan_cost = None
            uses_index = False
            index_name = None

        return QueryBenchmark(
            query_name=query_name,
            query=query,
            execution_time_ms=execution_time_ms,
            rows_returned=len(rows),
            plan_cost=plan_cost,
            uses_index=uses_index,
            index_name=index_name,
        )

    except Exception as e:
        logger.error(f"Failed to benchmark query {query_name}: {e}")
        return QueryBenchmark(
            query_name=query_name,
            query=query,
            execution_time_ms=-1,
            rows_returned=0,
        )


def run_benchmarks(session: Session) -> List[QueryBenchmark]:
    """Run all query benchmarks."""
    logger.info("Running query benchmarks...")
    benchmarks = []

    # Test parameters
    test_params = {
        "protocol": "mcp",
        "metadata_filter": json.dumps({"transport": "stdio"}),
        "schema_key": "type",
    }

    for query_name, query in QUERY_PATTERNS.items():
        benchmark = benchmark_query(session, query_name, query, test_params)
        benchmarks.append(benchmark)

        status = "✓" if benchmark.execution_time_ms >= 0 else "✗"
        logger.info(
            f"{status} {query_name}: {benchmark.execution_time_ms:.2f}ms, "
            f"{benchmark.rows_returned} rows, "
            f"index: {benchmark.uses_index}"
        )

    return benchmarks


def analyze_indexes(session: Session) -> Dict[str, List[str]]:
    """Analyze existing indexes."""
    logger.info("Analyzing existing indexes...")

    inspector = inspect(session.bind)
    index_info = {}

    for table in ["resources", "capabilities", "cost_tracking", "federation_nodes"]:
        if table in inspector.get_table_names():
            indexes = inspector.get_indexes(table)
            index_info[table] = [idx["name"] for idx in indexes]
            logger.info(f"  {table}: {len(indexes)} indexes")

    return index_info


def generate_recommendations(benchmarks: List[QueryBenchmark]) -> List[OptimizationRecommendation]:
    """Generate optimization recommendations based on benchmarks."""
    logger.info("Generating optimization recommendations...")
    recommendations = []

    # Check for slow queries (> 100ms)
    slow_queries = [b for b in benchmarks if b.execution_time_ms > 100]

    for benchmark in slow_queries:
        if not benchmark.uses_index:
            recommendations.append(
                OptimizationRecommendation(
                    query_pattern=benchmark.query_name,
                    current_performance_ms=benchmark.execution_time_ms,
                    recommendation=f"Add index for query pattern: {benchmark.query_name}",
                    estimated_improvement="50-90% faster",
                    priority="high",
                )
            )

    # Check for JSONB queries without GIN index
    jsonb_queries = [b for b in benchmarks if "@>" in b.query or "?" in b.query]
    for benchmark in jsonb_queries:
        if not benchmark.uses_index or "gin" not in str(benchmark.index_name).lower():
            recommendations.append(
                OptimizationRecommendation(
                    query_pattern=benchmark.query_name,
                    current_performance_ms=benchmark.execution_time_ms,
                    recommendation="Use GIN index for JSONB queries",
                    estimated_improvement="80-95% faster for large datasets",
                    priority="high",
                )
            )

    # Check for JOIN queries
    join_queries = [b for b in benchmarks if "JOIN" in b.query.upper()]
    for benchmark in join_queries:
        if benchmark.execution_time_ms > 50:
            recommendations.append(
                OptimizationRecommendation(
                    query_pattern=benchmark.query_name,
                    current_performance_ms=benchmark.execution_time_ms,
                    recommendation="Consider adding covering index or materialized view",
                    estimated_improvement="30-60% faster",
                    priority="medium" if benchmark.execution_time_ms < 200 else "high",
                )
            )

    return recommendations


def apply_optimizations(session: Session, dry_run: bool = True):
    """
    Apply recommended query optimizations.

    Creates additional indexes and query optimization structures.
    """
    logger.info("Applying query optimizations..." + (" (DRY RUN)" if dry_run else ""))

    optimizations = [
        # Partial index for active resources
        {
            "name": "ix_resources_protocol_active",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_resources_protocol_active
                ON resources (protocol, name)
                WHERE metadata->>'status' = 'active'
            """,
            "description": "Partial index for active resources by protocol",
        },

        # Covering index for capability lookups
        {
            "name": "ix_capabilities_resource_name_sensitivity",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_capabilities_resource_name_sensitivity
                ON capabilities (resource_id, name, sensitivity_level)
                INCLUDE (description)
            """,
            "description": "Covering index for capability lookups with resource_id",
        },

        # Expression index for JSONB type queries
        {
            "name": "ix_capabilities_input_schema_type",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_capabilities_input_schema_type
                ON capabilities ((input_schema->>'type'))
            """,
            "description": "Expression index for input schema type filtering",
        },

        # Composite index for cost analysis
        {
            "name": "ix_cost_tracking_principal_timestamp",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cost_tracking_principal_timestamp
                ON cost_tracking (principal_id, timestamp DESC, capability_id)
            """,
            "description": "Composite index for cost tracking queries",
        },

        # Statistics for query planner
        {
            "name": "stats_resources",
            "sql": "ANALYZE resources",
            "description": "Update table statistics for resources",
        },
        {
            "name": "stats_capabilities",
            "sql": "ANALYZE capabilities",
            "description": "Update table statistics for capabilities",
        },
    ]

    for opt in optimizations:
        logger.info(f"  {'[DRY RUN]' if dry_run else '[APPLY]'} {opt['description']}")

        if not dry_run:
            try:
                session.execute(text(opt["sql"]))
                session.commit()
                logger.info(f"    ✓ Applied: {opt['name']}")
            except Exception as e:
                logger.error(f"    ✗ Failed to apply {opt['name']}: {e}")
                session.rollback()


def generate_report(
    benchmarks: List[QueryBenchmark],
    recommendations: List[OptimizationRecommendation],
    index_info: Dict[str, List[str]],
) -> str:
    """Generate performance report."""
    report = []
    report.append("=" * 80)
    report.append("SARK v2.0 Polymorphic Query Performance Report")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now(UTC).isoformat()}")
    report.append("")

    # Index summary
    report.append("Index Summary")
    report.append("-" * 80)
    for table, indexes in index_info.items():
        report.append(f"{table}: {len(indexes)} indexes")
        for idx in indexes:
            report.append(f"  - {idx}")
    report.append("")

    # Benchmark results
    report.append("Query Benchmark Results")
    report.append("-" * 80)
    report.append(f"{'Query Name':<40} {'Time (ms)':<12} {'Rows':<8} {'Index Used':<12}")
    report.append("-" * 80)

    for b in sorted(benchmarks, key=lambda x: x.execution_time_ms, reverse=True):
        if b.execution_time_ms >= 0:
            report.append(
                f"{b.query_name:<40} "
                f"{b.execution_time_ms:>10.2f}ms "
                f"{b.rows_returned:>6} "
                f"{'✓' if b.uses_index else '✗':<12}"
            )
    report.append("")

    # Performance statistics
    valid_benchmarks = [b for b in benchmarks if b.execution_time_ms >= 0]
    if valid_benchmarks:
        avg_time = sum(b.execution_time_ms for b in valid_benchmarks) / len(valid_benchmarks)
        max_time = max(b.execution_time_ms for b in valid_benchmarks)
        min_time = min(b.execution_time_ms for b in valid_benchmarks)

        report.append("Performance Statistics")
        report.append("-" * 80)
        report.append(f"Average query time: {avg_time:.2f}ms")
        report.append(f"Min query time: {min_time:.2f}ms")
        report.append(f"Max query time: {max_time:.2f}ms")
        report.append(f"Queries using indexes: {sum(1 for b in valid_benchmarks if b.uses_index)}/{len(valid_benchmarks)}")
        report.append("")

    # Recommendations
    report.append("Optimization Recommendations")
    report.append("-" * 80)

    if recommendations:
        high_priority = [r for r in recommendations if r.priority == "high"]
        medium_priority = [r for r in recommendations if r.priority == "medium"]

        if high_priority:
            report.append("\nHIGH PRIORITY:")
            for r in high_priority:
                report.append(f"  - {r.query_pattern} ({r.current_performance_ms:.2f}ms)")
                report.append(f"    {r.recommendation}")
                report.append(f"    Estimated improvement: {r.estimated_improvement}")

        if medium_priority:
            report.append("\nMEDIUM PRIORITY:")
            for r in medium_priority:
                report.append(f"  - {r.query_pattern} ({r.current_performance_ms:.2f}ms)")
                report.append(f"    {r.recommendation}")
                report.append(f"    Estimated improvement: {r.estimated_improvement}")
    else:
        report.append("No optimization recommendations - queries are performing well!")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SARK v2.0 polymorphic query optimization")
    parser.add_argument("--analyze", action="store_true", help="Analyze current indexes")
    parser.add_argument("--benchmark", action="store_true", help="Run query benchmarks")
    parser.add_argument("--optimize", action="store_true", help="Apply optimizations")
    parser.add_argument("--report", action="store_true", help="Generate performance report")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't apply changes)")
    parser.add_argument("--output", type=str, help="Output file for report")

    args = parser.parse_args()

    # Default to report if no action specified
    if not any([args.analyze, args.benchmark, args.optimize, args.report]):
        args.report = True
        args.analyze = True
        args.benchmark = True

    try:
        session = create_session()

        index_info = {}
        benchmarks = []
        recommendations = []

        if args.analyze or args.report:
            index_info = analyze_indexes(session)

        if args.benchmark or args.report:
            benchmarks = run_benchmarks(session)
            recommendations = generate_recommendations(benchmarks)

        if args.optimize:
            apply_optimizations(session, dry_run=args.dry_run)

        if args.report:
            report = generate_report(benchmarks, recommendations, index_info)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(report)
                logger.info(f"Report written to {args.output}")
            else:
                print("\n" + report)

        return 0

    except Exception as e:
        logger.exception(f"Optimization tool failed: {e}")
        return 1

    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    sys.exit(main())
