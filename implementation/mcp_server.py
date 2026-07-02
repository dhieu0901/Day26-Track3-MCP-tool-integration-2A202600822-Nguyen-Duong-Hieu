import json
import os
import sys
from fastmcp import FastMCP
from db import SQLiteAdapter, ValidationError

# Initialize the server. We specify dynamic server name.
mcp = FastMCP("SQLite Lab MCP Server")

# Instantiate the SQLite Adapter
# Resolve database path relative to this server file
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "sqlite_lab.db")
adapter = SQLiteAdapter(db_path=db_path)

@mcp.tool(name="search")
def search(
    table: str,
    filters: list | dict = None,
    columns: list = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str = None,
    descending: bool = False
):
    """
    Search database records in a given table.
    
    Arguments:
    - table: Name of the table to search (e.g. 'students', 'courses', 'enrollments')
    - filters: A dictionary of key-value pairs (implied '=') or a list of dictionaries with 'column', 'operator', 'value'
               Example filters list: [{"column": "cohort", "operator": "=", "value": "A1"}]
    - columns: List of specific column names to retrieve. If empty, retrieves all columns.
    - limit: Maximum number of rows to return (default 20, must be positive).
    - offset: Number of rows to skip (default 0).
    - order_by: Column name to sort the results by.
    - descending: Sort descending if True, ascending if False.
    """
    try:
        results = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending
        )
        return results
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")
    except Exception as e:
        raise ValueError(f"Internal Database Error: {e}")

@mcp.tool(name="insert")
def insert(table: str, values: dict):
    """
    Insert a record into a table and return the inserted row.
    
    Arguments:
    - table: Name of the table to insert into.
    - values: Dict mapping column name to values. Cannot be empty.
    """
    try:
        results = adapter.insert(table=table, values=values)
        return results
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")
    except Exception as e:
        raise ValueError(f"Internal Database Error: {e}")

@mcp.tool(name="aggregate")
def aggregate(table: str, metric: str, column: str = None, filters: list | dict = None, group_by: str | list = None):
    """
    Perform aggregate queries (COUNT, AVG, SUM, MIN, MAX).
    
    Arguments:
    - table: Name of the table.
    - metric: The metric function (COUNT, AVG, SUM, MIN, MAX).
    - column: Column name to apply the metric on (default '*' for COUNT, required for other metrics).
    - filters: Filters to apply before aggregate calculation.
    - group_by: Column or list of columns to group the results by.
    """
    try:
        results = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by
        )
        return results
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")
    except Exception as e:
        raise ValueError(f"Internal Database Error: {e}")

@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Exposes the full database schema (all table and column definitions).
    """
    try:
        tables = adapter.list_tables()
        full_schema = {}
        for t in tables:
            full_schema[t] = adapter.get_table_schema(t)
        return json.dumps(full_schema, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Internal Database Error: {e}"})

@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Exposes the schema for a specific database table.
    """
    try:
        schema = adapter.get_table_schema(table_name)
        return json.dumps(schema, indent=2)
    except ValidationError as e:
        return json.dumps({"error": f"Validation Error: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Internal Database Error: {e}"})

if __name__ == "__main__":
    mcp.run()
