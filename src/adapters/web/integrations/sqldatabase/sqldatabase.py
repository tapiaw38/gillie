"""
PostgreSQL Database Integration

Supports both read-only SELECT queries via `query()` and configurable
raw SQL execution via `execute()`.

Security layers:
  1. DDL/DCL keywords are ALWAYS blocked (DROP, TRUNCATE, ALTER, CREATE,
     GRANT, REVOKE, EXEC, EXECUTE).
  2. DML keywords (INSERT, UPDATE, DELETE) are blocked by default but can
     be selectively allowed via the `blocked_keywords` constructor parameter.
  3. For `query()`, only allowed tables may be referenced and only SELECT
     statements are built internally.
  4. For `execute()`, comment markers (-- and /*) and multiple statements
     (more than one semicolon) are always rejected.
"""

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# These are ALWAYS blocked regardless of user config
_ALWAYS_BLOCKED = frozenset([
    "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
    "EXEC", "EXECUTE",
])

# DML operations that are blocked by default but may be unlocked per integration
_DEFAULT_BLOCKED_DML = frozenset(["INSERT", "UPDATE", "DELETE"])

# Full set of DML operations tracked for `allowed_operations`
_ALL_DML = frozenset(["INSERT", "UPDATE", "DELETE"])


class SQLDatabaseIntegration:
    """
    Async PostgreSQL integration with configurable DML restrictions.

    Args:
        connection_string: asyncpg-compatible DSN
            e.g. "postgresql://user:pass@host:5432/dbname"
        allowed_tables: list of dicts with keys 'name' and 'description'
            e.g. [{"name": "products", "description": "Product catalog..."}]
        blocked_keywords: list of SQL keywords to block in `execute()` in
            addition to the always-blocked set.  Defaults to blocking all DML
            (INSERT, UPDATE, DELETE).  Pass an empty list to allow all DML.
    """

    def __init__(
        self,
        connection_string: str,
        allowed_tables: List[Dict[str, str]],
        blocked_keywords: List[str] = None,
    ):
        self.connection_string = connection_string
        # Normalize: name → lowercase, description → str
        self._tables: Dict[str, str] = {
            t["name"].strip().lower(): t.get("description", "")
            for t in allowed_tables
            if t.get("name")
        }

        # Merge caller-supplied keywords with the always-blocked set.
        # When the caller passes None we apply the safe default (block all DML).
        caller_blocked = (
            {k.upper() for k in blocked_keywords}
            if blocked_keywords is not None
            else _DEFAULT_BLOCKED_DML
        )
        self.blocked_keywords: frozenset = _ALWAYS_BLOCKED | caller_blocked

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def table_names(self) -> List[str]:
        return list(self._tables.keys())

    @property
    def tables_info(self) -> Dict[str, str]:
        """Map of table_name → description."""
        return dict(self._tables)

    @property
    def allowed_operations(self) -> List[str]:
        """DML operations not present in blocked_keywords (SELECT is always allowed)."""
        ops = ["SELECT"]
        for dml in sorted(_ALL_DML):
            if dml not in self.blocked_keywords:
                ops.append(dml)
        return ops

    # Keep for backward compat (first table)
    @property
    def allowed_table(self) -> str:
        return self.table_names[0] if self.table_names else ""

    @property
    def table_description(self) -> str:
        return self._tables.get(self.allowed_table, "")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def query(
        self,
        table: str,
        columns: List[str],
        filters: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Execute a safe SELECT on the specified table.

        Args:
            table: table name (must be in allowed_tables)
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

        target = table.strip().lower()
        if target not in self._tables:
            return {
                "success": False,
                "error": f"Table '{table}' is not in allowed tables: {self.table_names}",
            }

        try:
            sql = self._build_query(target, columns, filters, min(limit, 50))
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

    async def execute(self, sql: str) -> Dict[str, Any]:
        """
        Execute an arbitrary SQL statement subject to the configured restrictions.

        Security checks applied before execution:
          - The statement must not be empty.
          - No keyword in `self.blocked_keywords` may appear as a whole word.
          - SQL comment markers (-- and /*) are always rejected.
          - More than one semicolon (i.e. multiple statements) is rejected.

        Args:
            sql: the full SQL statement to run.

        Returns:
            For SELECT: {"success": True, "rows": [...], "total": N}
            For DML:    {"success": True, "status": "<pg status>", "message": "..."}
            On error:   {"success": False, "error": "..."}
        """
        try:
            import asyncpg
        except ImportError:
            return {"success": False, "error": "asyncpg is not installed. Run: pip install asyncpg"}

        sql = sql.strip()
        if not sql:
            return {"success": False, "error": "La sentencia SQL no puede estar vacía."}

        # --- security: blocked keywords (whole-word match) ---
        sql_upper = sql.upper()
        for kw in self.blocked_keywords:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, sql_upper):
                return {
                    "success": False,
                    "error": (
                        f"Operación no permitida: '{kw}' está bloqueado en esta integración."
                    ),
                }

        # --- security: comment markers (not word-bounded) ---
        if "--" in sql or "/*" in sql:
            return {
                "success": False,
                "error": "Operación no permitida: los comentarios SQL están bloqueados.",
            }

        # --- security: multiple statements ---
        if sql.count(";") > 1:
            return {
                "success": False,
                "error": "Operación no permitida: solo se permite una sentencia por llamada.",
            }

        is_select = sql_upper.lstrip().startswith("SELECT")

        try:
            logger.info(f"[sqldatabase] execute(): {sql[:200]}")
            conn = await asyncpg.connect(self.connection_string)
            try:
                if is_select:
                    rows = await conn.fetch(sql)
                    result = [self._serialize_row(dict(row)) for row in rows]
                    logger.info(f"[sqldatabase] execute() returned {len(result)} rows")
                    return {"success": True, "rows": result, "total": len(result)}
                else:
                    status = await conn.execute(sql)
                    logger.info(f"[sqldatabase] execute() status: {status}")
                    return {
                        "success": True,
                        "status": status,
                        "message": "Operación ejecutada correctamente",
                    }
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"[sqldatabase] execute() error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_query(
        self,
        table: str,
        columns: List[str],
        filters: Optional[str],
        limit: int,
    ) -> str:
        safe_columns = self._sanitize_columns(columns)
        col_str = ", ".join(safe_columns) if safe_columns else "*"
        sql = f"SELECT {col_str} FROM {table}"

        if filters:
            self._validate_filters(filters, table)
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

    def _validate_filters(self, filters: str, table: str) -> None:
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
        for ref in from_matches:
            if ref.lower() != table:
                raise ValueError(
                    f"Filter references unauthorized table: {ref!r}. "
                    f"Only '{table}' is allowed in this query."
                )
