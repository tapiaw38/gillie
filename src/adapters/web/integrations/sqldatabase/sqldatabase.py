"""
PostgreSQL Database Integration

Read-only integration for querying a single allowed table.
Security layers:
  1. Only SELECT statements are accepted.
  2. Only the configured allowed_table may appear in the FROM clause.
  3. The database user should have SELECT privileges on that table only.
"""

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SQLDatabaseIntegration:
    """
    Async PostgreSQL integration restricted to SELECT queries on one table.

    Args:
        connection_string: asyncpg-compatible DSN
            e.g. "postgresql://user:pass@host:5432/dbname"
        allowed_table: the only table the AI is allowed to query
        table_description: human-readable description of columns/purpose
            used to build the tool description shown to the LLM
    """

    def __init__(
        self,
        connection_string: str,
        allowed_table: str,
        table_description: str = "",
    ):
        self.connection_string = connection_string
        self.allowed_table = allowed_table.strip().lower()
        self.table_description = table_description

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def query(
        self,
        columns: List[str],
        filters: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Execute a safe SELECT on the allowed table.

        Args:
            columns: list of column names to retrieve; ["*"] means all
            filters: optional WHERE clause fragment, e.g. "nombre ILIKE '%leche%'"
            limit: max rows to return (capped at 50)

        Returns:
            {"success": True, "rows": [...], "total": N}
            or
            {"success": False, "error": "..."}
        """
        try:
            import asyncpg
        except ImportError:
            return {"success": False, "error": "asyncpg is not installed. Run: pip install asyncpg"}

        try:
            sql = self._build_query(columns, filters, min(limit, 50))
            logger.info(f"[sqldatabase] Executing: {sql}")

            conn = await asyncpg.connect(self.connection_string)
            try:
                rows = await conn.fetch(sql)
                result = [self._serialize_row(dict(row)) for row in rows]
                logger.info(f"[sqldatabase] Returned {len(result)} rows")
                return {"success": True, "rows": result, "total": len(result)}
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"[sqldatabase] Query error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_query(
        self,
        columns: List[str],
        filters: Optional[str],
        limit: int,
    ) -> str:
        safe_columns = self._sanitize_columns(columns)
        col_str = ", ".join(safe_columns) if safe_columns else "*"
        sql = f"SELECT {col_str} FROM {self.allowed_table}"

        if filters:
            self._validate_filters(filters)
            sql += f" WHERE {filters}"

        sql += f" LIMIT {int(limit)}"
        return sql

    def _sanitize_columns(self, columns: List[str]) -> List[str]:
        """Allow only simple identifiers and * ."""
        safe = []
        for col in columns:
            col = col.strip()
            if col == "*":
                return ["*"]
            if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", col):
                safe.append(col)
            else:
                logger.warning(f"[sqldatabase] Rejected column name: {col!r}")
        return safe or ["*"]

    @staticmethod
    def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert non-JSON-serializable types (UUID, datetime) to strings."""
        result = {}
        for k, v in row.items():
            if isinstance(v, uuid.UUID):
                result[k] = str(v)
            elif hasattr(v, "isoformat"):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result

    def _validate_filters(self, filters: str) -> None:
        """
        Reject filters that reference other tables or contain dangerous keywords.
        Raises ValueError if validation fails.
        """
        upper = filters.upper()

        blocked_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
            "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC",
            "EXECUTE", "--", ";", "/*",
        ]
        for kw in blocked_keywords:
            if kw in upper:
                raise ValueError(f"Forbidden keyword in filter: {kw!r}")

        # Detect subqueries referencing other tables
        from_matches = re.findall(r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)", upper)
        for table in from_matches:
            if table.lower() != self.allowed_table:
                raise ValueError(
                    f"Filter references unauthorized table: {table!r}. "
                    f"Only '{self.allowed_table}' is allowed."
                )
