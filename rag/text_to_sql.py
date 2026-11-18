"""Read-only text-to-SQL tools for the Snowflake TPC-H sample database."""

import json
import re

import sqlglot
from sqlglot import exp
from langchain_core.tools import tool

from rag import config


MAX_ROWS = 100
QUERY_TIMEOUT_SECONDS = 30


def safe_identifier(value):
    """Validate a Snowflake database, schema, or table identifier."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", value or ""):
        raise ValueError(f"Invalid SQL identifier: {value}")
    return value.upper()


def connect_sql():
    import snowflake.connector
    from rag import config
    from rag.snowflake_store import load_private_key

    return snowflake.connector.connect(
        account=config.get("SNOWFLAKE_ACCOUNT"),
        user=config.get("SNOWFLAKE_USER"),
        role=config.get("SNOWFLAKE_ROLE"),
        warehouse=config.get("SNOWFLAKE_WAREHOUSE"),
        database=config.get("SNOWFLAKE_SQL_DATABASE"),
        schema=config.get("SNOWFLAKE_SQL_SCHEMA"),
        private_key=load_private_key(),
    )


def list_tables(conn):
    """List base tables in the configured analytical schema."""
    database = safe_identifier(config.get("SNOWFLAKE_SQL_DATABASE"))
    schema = safe_identifier(config.get("SNOWFLAKE_SQL_SCHEMA"))

    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT TABLE_NAME
            FROM {database}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """,
            (schema,),
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()


def list_columns(conn, table_name):
    """Return column names and types for an allowed analytical table."""
    table = safe_identifier(table_name)

    if table not in list_tables(conn):
        raise ValueError(
            f"Table '{table}' is not available in the configured SQL schema."
        )

    database = safe_identifier(config.get("SNOWFLAKE_SQL_DATABASE"))
    schema = safe_identifier(config.get("SNOWFLAKE_SQL_SCHEMA"))

    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM {database}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (schema, table),
        )
        return [
            {"column": row[0], "type": row[1]}
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()


def validate_sql(sql, conn):
    """Validate a single read-only SELECT against the configured schema."""
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

    statements = sqlglot.parse(sql, read="snowflake")

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Only one SQL statement is allowed.")

    tree = statements[0]

    # Only SELECT statements, including SELECT statements with CTEs, are allowed.
    if not isinstance(tree, exp.Select):
        raise ValueError("Only SELECT queries and WITH ... SELECT queries are allowed.")

    # Reject potentially unsafe operations embedded in a query.
    forbidden = tuple(
        getattr(exp, name)
        for name in (
            "Insert",
            "Update",
            "Delete",
            "Merge",
            "Create",
            "Drop",
            "Alter",
            "Command",
            "Copy",
            "Transaction",
            "Into",
        )
        if hasattr(exp, name)
    )

    for node in tree.walk():
        if isinstance(node, forbidden):
            raise ValueError("The query contains a prohibited SQL operation.")

    # Restrict all physical tables to the configured database and schema.
    database = safe_identifier(config.get("SNOWFLAKE_SQL_DATABASE"))
    schema = safe_identifier(config.get("SNOWFLAKE_SQL_SCHEMA"))
    allowed_tables = set(list_tables(conn))

    cte_names = {
        cte.alias_or_name.upper()
        for cte in tree.find_all(exp.CTE)
    }

    for table in tree.find_all(exp.Table):
        # Only ordinary table identifiers are supported.
        if not isinstance(table.this, exp.Identifier):
            raise ValueError("Table functions and nonstandard table references are not allowed.")

        table_name = table.name.upper()

        # A CTE is a temporary query result, not a physical table.
        if table_name in cte_names and not table.db and not table.catalog:
            continue

        table_schema = table.db.upper() if table.db else schema
        table_database = table.catalog.upper() if table.catalog else database

        if table_database != database or table_schema != schema:
            raise ValueError(
                f"Access is restricted to {database}.{schema}."
            )

        if table_name not in allowed_tables:
            raise ValueError(f"Table '{table_name}' does not exist in {database}.{schema}.")

    # Add a default limit or reduce an excessive user-supplied limit.
    limit = tree.args.get("limit")

    if limit is None:
        tree = tree.limit(MAX_ROWS)
    else:
        expression = limit.expression
        if not isinstance(expression, exp.Literal) or not expression.is_int:
            raise ValueError("LIMIT must be a positive integer.")
        requested_limit = int(expression.this)
        if requested_limit < 1:
            raise ValueError("LIMIT must be greater than zero.")
        if requested_limit > MAX_ROWS:
            tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="snowflake")


def execute_sql(conn, sql):
    """Execute validated read-only SQL and return a structured result."""
    safe_sql = validate_sql(sql, conn)

    cursor = conn.cursor()
    try:
        cursor.execute(safe_sql, timeout=QUERY_TIMEOUT_SECONDS)

        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS)

        result = {
            "type": "sql_result",
            "sql": safe_sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": len(rows) == MAX_ROWS,
        }

        # Convert Snowflake-specific values into JSON-compatible values.
        result["rows"] = [
            [
                value.isoformat() if hasattr(value, "isoformat")
                else str(value) if value is not None and not isinstance(
                    value, (str, int, float, bool)
                )
                else value
                for value in row
            ]
            for row in result["rows"]
        ]

        return json.dumps(result, default=str)

    finally:
        cursor.close()


def build_sql_tools(conn):
    """Create the three Snowflake tools for the LangGraph agent."""

    @tool
    def snowflake_table_lookup() -> str:
        """List available analytical tables in the configured Snowflake schema.

        Call this before writing SQL when you need to discover available tables.
        """
        try:
            tables = list_tables(conn)
            return json.dumps({
                "type": "table_list",
                "database": config.get("SNOWFLAKE_SQL_DATABASE"),
                "schema": config.get("SNOWFLAKE_SQL_SCHEMA"),
                "tables": tables,
            })
        except Exception as e:
            return f"Snowflake table lookup failed: {e}"

    @tool
    def snowflake_column_lookup(table_name: str) -> str:
        """Retrieve column names and data types for a Snowflake table.

        Args:
            table_name: The name of an available table, such as CUSTOMER or ORDERS.
        """
        try:
            columns = list_columns(conn, table_name)
            return json.dumps({
                "type": "column_list",
                "table": safe_identifier(table_name),
                "columns": columns,
            })
        except Exception as e:
            return f"Snowflake column lookup failed: {e}"

    @tool
    def snowflake_execute_sql(sql: str) -> str:
        """Execute one validated, read-only SQL query against Snowflake.

        Args:
            sql: A single SELECT or WITH ... SELECT query.
        """
        try:
            return execute_sql(conn, sql)
        except Exception as e:
            return f"Snowflake SQL execution failed: {e}"

    return [
        snowflake_table_lookup,
        snowflake_column_lookup,
        snowflake_execute_sql,
    ]