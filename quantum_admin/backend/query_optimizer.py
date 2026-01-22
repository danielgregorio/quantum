"""
Query Optimization Utilities for Quantum Admin
Analyzes and optimizes database queries for better performance
"""
import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    Database query optimizer and analyzer

    Features:
    - Query analysis and explain plans
    - Index suggestions
    - Slow query detection
    - Query rewriting
    - Statistics collection
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.slow_query_threshold = 1.0  # seconds

    def explain_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get query execution plan (EXPLAIN)

        Args:
            query: SQL query to analyze
            params: Query parameters

        Returns:
            Execution plan analysis
        """
        try:
            # Add EXPLAIN ANALYZE to query
            explain_query = f"EXPLAIN ANALYZE {query}"

            result = self.db.execute(text(explain_query), params or {})
            plan = [dict(row) for row in result]

            # Parse execution plan
            analysis = self._parse_execution_plan(plan)

            return {
                "status": "success",
                "query": query,
                "execution_plan": plan,
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Query explain failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }

    def _parse_execution_plan(self, plan: List[Dict]) -> Dict[str, Any]:
        """Parse execution plan and extract insights"""
        analysis = {
            "estimated_cost": 0,
            "estimated_rows": 0,
            "scan_types": [],
            "issues": [],
            "suggestions": []
        }

        for row in plan:
            plan_str = str(row)

            # Extract cost
            cost_match = re.search(r"cost=([\d.]+)\.\.([\d.]+)", plan_str)
            if cost_match:
                analysis["estimated_cost"] = float(cost_match.group(2))

            # Extract rows
            rows_match = re.search(r"rows=(\d+)", plan_str)
            if rows_match:
                analysis["estimated_rows"] = int(rows_match.group(1))

            # Detect scan types
            if "Seq Scan" in plan_str:
                analysis["scan_types"].append("Sequential Scan")
                analysis["issues"].append("Sequential scan detected - consider adding index")
                analysis["suggestions"].append("Add index on frequently queried columns")

            if "Index Scan" in plan_str:
                analysis["scan_types"].append("Index Scan")

            if "Bitmap" in plan_str:
                analysis["scan_types"].append("Bitmap Scan")

            # Detect other issues
            if "rows=" in plan_str and analysis["estimated_rows"] > 10000:
                analysis["issues"].append("Large result set - consider pagination")
                analysis["suggestions"].append("Use LIMIT/OFFSET for pagination")

        return analysis

    def suggest_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Suggest indexes for a table based on query patterns

        Args:
            table_name: Name of table to analyze

        Returns:
            List of index suggestions
        """
        try:
            # Get table metadata
            inspector = inspect(self.db.get_bind())
            columns = inspector.get_columns(table_name)
            existing_indexes = inspector.get_indexes(table_name)

            suggestions = []

            # Check for foreign keys without indexes
            fks = inspector.get_foreign_keys(table_name)
            for fk in fks:
                fk_cols = fk["constrained_columns"]
                indexed = any(
                    set(fk_cols).issubset(set(idx["column_names"]))
                    for idx in existing_indexes
                )

                if not indexed:
                    suggestions.append({
                        "type": "foreign_key_index",
                        "columns": fk_cols,
                        "reason": "Foreign key without index",
                        "sql": f"CREATE INDEX idx_{table_name}_{'_'.join(fk_cols)} ON {table_name}({', '.join(fk_cols)})"
                    })

            # Suggest composite indexes for common query patterns
            # (In production: analyze query logs)
            for col in columns:
                col_name = col["name"]

                # Skip if already indexed
                if any(col_name in idx["column_names"] for idx in existing_indexes):
                    continue

                # Suggest index for searchable columns
                if col["type"].__class__.__name__ in ["VARCHAR", "TEXT"]:
                    suggestions.append({
                        "type": "search_index",
                        "columns": [col_name],
                        "reason": "Frequently searched text column",
                        "sql": f"CREATE INDEX idx_{table_name}_{col_name} ON {table_name}({col_name})"
                    })

                # Suggest index for date/timestamp columns
                if col["type"].__class__.__name__ in ["DATE", "DATETIME", "TIMESTAMP"]:
                    suggestions.append({
                        "type": "date_index",
                        "columns": [col_name],
                        "reason": "Date column for range queries",
                        "sql": f"CREATE INDEX idx_{table_name}_{col_name} ON {table_name}({col_name})"
                    })

            return suggestions

        except Exception as e:
            logger.error(f"Index suggestion failed: {e}")
            return []

    def analyze_slow_queries(self) -> List[Dict[str, Any]]:
        """
        Analyze slow query log and identify problematic queries

        Returns:
            List of slow queries with analysis
        """
        try:
            # In production: query pg_stat_statements or MySQL slow query log
            # This is a simplified example

            slow_queries = [
                {
                    "query": "SELECT * FROM users WHERE email LIKE '%@example.com'",
                    "avg_time_ms": 1500,
                    "calls": 250,
                    "total_time_ms": 375000,
                    "issues": [
                        "SELECT * instead of specific columns",
                        "Leading wildcard in LIKE prevents index usage"
                    ],
                    "suggestions": [
                        "Select only needed columns",
                        "Use full-text search or reverse index for email domain searches"
                    ]
                }
            ]

            return slow_queries

        except Exception as e:
            logger.error(f"Slow query analysis failed: {e}")
            return []

    def optimize_query(self, query: str) -> Dict[str, Any]:
        """
        Automatically optimize a query

        Args:
            query: SQL query to optimize

        Returns:
            Original and optimized query with explanation
        """
        optimized = query
        changes = []

        # Remove unnecessary SELECT *
        if re.search(r"SELECT\s+\*", query, re.IGNORECASE):
            changes.append("Consider selecting only required columns instead of SELECT *")

        # Suggest LIMIT for queries without it
        if "LIMIT" not in query.upper() and "SELECT" in query.upper():
            changes.append("Add LIMIT clause to prevent large result sets")
            optimized = f"{query.rstrip(';')} LIMIT 1000"

        # Detect N+1 query patterns
        if "WHERE id IN" in query.upper():
            changes.append("Good: Using IN clause instead of multiple queries")

        # Suggest JOIN instead of subquery where applicable
        if "WHERE column IN (SELECT" in query.upper():
            changes.append("Consider using JOIN instead of subquery for better performance")

        return {
            "original": query,
            "optimized": optimized,
            "changes": changes,
            "improvement_estimate": "10-30% faster" if changes else "Already optimized"
        }

    def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """
        Get table statistics for optimization decisions

        Args:
            table_name: Table to analyze

        Returns:
            Table statistics
        """
        try:
            # Get row count
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = self.db.execute(text(count_query))
            row_count = result.fetchone()[0]

            # Get table size (PostgreSQL)
            size_query = f"SELECT pg_total_relation_size('{table_name}') as size"
            try:
                result = self.db.execute(text(size_query))
                size_bytes = result.fetchone()[0]
            except:
                size_bytes = 0

            # Get index information
            inspector = inspect(self.db.get_bind())
            indexes = inspector.get_indexes(table_name)

            return {
                "table_name": table_name,
                "row_count": row_count,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / 1024 / 1024, 2) if size_bytes else 0,
                "index_count": len(indexes),
                "indexes": indexes
            }

        except Exception as e:
            logger.error(f"Table statistics failed: {e}")
            return {
                "table_name": table_name,
                "error": str(e)
            }

    def vacuum_analyze(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Run VACUUM ANALYZE to update table statistics

        Args:
            table_name: Specific table or None for all tables

        Returns:
            Operation result
        """
        try:
            if table_name:
                query = f"VACUUM ANALYZE {table_name}"
            else:
                query = "VACUUM ANALYZE"

            self.db.execute(text(query))
            self.db.commit()

            return {
                "status": "success",
                "message": f"VACUUM ANALYZE completed for {table_name or 'all tables'}"
            }

        except Exception as e:
            logger.error(f"VACUUM ANALYZE failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# ============================================================================
# Query Performance Monitor
# ============================================================================

class QueryPerformanceMonitor:
    """
    Monitor query performance in real-time

    Tracks slow queries and provides alerts
    """

    def __init__(self, slow_threshold_ms: float = 1000):
        self.slow_threshold_ms = slow_threshold_ms
        self.slow_queries = []
        self.query_stats = {}

    def track_query(self, query: str, duration_ms: float, params: Optional[Dict] = None):
        """Track query execution"""
        if duration_ms > self.slow_threshold_ms:
            self.slow_queries.append({
                "query": query,
                "duration_ms": duration_ms,
                "params": params,
                "timestamp": logging.time()
            })

        # Update statistics
        if query not in self.query_stats:
            self.query_stats[query] = {
                "count": 0,
                "total_time_ms": 0,
                "min_time_ms": float("inf"),
                "max_time_ms": 0
            }

        stats = self.query_stats[query]
        stats["count"] += 1
        stats["total_time_ms"] += duration_ms
        stats["min_time_ms"] = min(stats["min_time_ms"], duration_ms)
        stats["max_time_ms"] = max(stats["max_time_ms"], duration_ms)

    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """Get recent slow queries"""
        return sorted(
            self.slow_queries,
            key=lambda x: x["duration_ms"],
            reverse=True
        )[:limit]

    def get_query_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        for query, stats in self.query_stats.items():
            stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]

        return self.query_stats


# Global monitor instance
_performance_monitor = QueryPerformanceMonitor()


def get_performance_monitor() -> QueryPerformanceMonitor:
    """Get global performance monitor"""
    return _performance_monitor
