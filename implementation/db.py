import os
import sqlite3

class ValidationError(Exception):
    """Exception raised when a validation error occurs."""
    pass

class SQLiteAdapter:
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to the sqlite_lab.db in the same folder
            db_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(db_dir, "sqlite_lab.db")
        self.db_path = db_path
        self.allowed_operators = {"=", "!=", ">", ">=", "<", "<=", "LIKE", "IN"}
        self.allowed_metrics = {"COUNT", "AVG", "SUM", "MIN", "MAX"}

    def connect(self):
        """Returns a connection to the SQLite database with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys support
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def list_tables(self):
        """Returns a list of table names in the database."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row["name"] for row in cursor.fetchall()]
            return tables
        finally:
            conn.close()

    def get_table_schema(self, table_name):
        """
        Returns schema information for the specified table as a list of dicts.
        Raises ValidationError if table name is not valid.
        """
        # Validate table name against database tables to avoid SQL injection
        tables = self.list_tables()
        if table_name not in tables:
            raise ValidationError(f"Table '{table_name}' does not exist in database.")

        conn = self.connect()
        try:
            cursor = conn.cursor()
            # table_name is whitelisted above, so formatting it here is safe.
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "dflt_value": row["dflt_value"],
                    "pk": bool(row["pk"])
                })
            return columns
        finally:
            conn.close()

    def _validate_table_and_columns(self, table, check_columns=None):
        """
        Validates table existence and checks if column names exist in the table.
        Returns a dict of {column_name: column_info} for the table.
        """
        schema = self.get_table_schema(table)  # Raises ValidationError if table does not exist
        schema_dict = {col["name"]: col for col in schema}
        if check_columns:
            for col in check_columns:
                if col not in schema_dict:
                    raise ValidationError(f"Column '{col}' does not exist in table '{table}'.")
        return schema_dict

    def _parse_filters(self, table, schema_dict, filters):
        """
        Parses filter structures, validates column names, operators, and parameters.
        Returns (where_clause_str, parameter_tuple).
        """
        if not filters:
            return "", ()

        normalized_filters = []
        if isinstance(filters, dict):
            for col, val in filters.items():
                normalized_filters.append({"column": col, "operator": "=", "value": val})
        elif isinstance(filters, list):
            for f in filters:
                if not isinstance(f, dict) or "column" not in f or "operator" not in f or "value" not in f:
                    raise ValidationError("Each filter must be a dict containing 'column', 'operator', and 'value' keys.")
                normalized_filters.append(f)
        else:
            raise ValidationError("Filters must be either a dictionary or a list of filter dictionaries.")

        where_parts = []
        params = []

        for f in normalized_filters:
            col = f["column"]
            op = f["operator"].strip().upper()
            val = f["value"]

            # Validate column existence
            if col not in schema_dict:
                raise ValidationError(f"Filter column '{col}' does not exist in table '{table}'.")

            # Validate operator
            if op not in self.allowed_operators:
                raise ValidationError(f"Unsupported filter operator '{op}'. Allowed operators are {self.allowed_operators}.")

            if op == "IN":
                if not isinstance(val, (list, tuple)):
                    raise ValidationError(f"Value for 'IN' operator must be a list or tuple, got {type(val).__name__}.")
                if len(val) == 0:
                    # In SQLite, "col IN ()" is syntax error. We handle empty list safely
                    where_parts.append("1 = 0")
                else:
                    placeholders = ",".join(["?"] * len(val))
                    where_parts.append(f"{col} IN ({placeholders})")
                    params.extend(val)
            else:
                where_parts.append(f"{col} {op} ?")
                params.append(val)

        where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""
        return where_clause, tuple(params)

    def search(self, table, columns=None, filters=None, limit=20, offset=0, order_by=None, descending=False):
        """
        Performs a search query with strict validation.
        """
        # Validate table name and columns
        schema_dict = self._validate_table_and_columns(table, columns)

        # Parse and validate columns select list
        if columns:
            columns_str = ", ".join(columns)
        else:
            columns_str = "*"

        # Validate limit and offset
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError(f"Limit must be a non-negative integer, got {limit}.")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError(f"Offset must be a non-negative integer, got {offset}.")

        # Validate order_by
        if order_by:
            if order_by not in schema_dict:
                raise ValidationError(f"Order by column '{order_by}' does not exist in table '{table}'.")
            order_by_str = f" ORDER BY {order_by}"
            if descending:
                order_by_str += " DESC"
        else:
            order_by_str = ""

        # Parse and validate filters
        where_clause, params = self._parse_filters(table, schema_dict, filters)

        # Build final SQL string safely using whitelisted names
        sql = f"SELECT {columns_str} FROM {table}{where_clause}{order_by_str} LIMIT ? OFFSET ?;"
        full_params = params + (limit, offset)

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, full_params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def insert(self, table, values):
        """
        Inserts a row into the database, validates columns, and returns the inserted row.
        """
        if not values or not isinstance(values, dict):
            raise ValidationError("Values to insert must be a non-empty dictionary.")

        # Validate table and columns to insert
        schema_dict = self._validate_table_and_columns(table, list(values.keys()))

        cols = list(values.keys())
        placeholders = ", ".join(["?"] * len(cols))
        cols_str = ", ".join(cols)

        sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders});"
        params = tuple(values.values())

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            last_id = cursor.lastrowid
            conn.commit()

            # Retrieve the inserted row using rowid (available in sqlite for tables with AUTOINCREMENT or standard tables)
            cursor.execute(f"SELECT * FROM {table} WHERE rowid = ?;", (last_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise ValidationError(f"Integrity check failed during insertion: {e}")
        except Exception as e:
            conn.rollback()
            raise ValidationError(f"Failed to insert row: {e}")
        finally:
            conn.close()

    def aggregate(self, table, metric, column=None, filters=None, group_by=None):
        """
        Runs aggregation queries (COUNT, AVG, SUM, MIN, MAX) with options for filters and group_by.
        """
        # Validate table
        schema_dict = self._validate_table_and_columns(table)

        # Validate metric
        metric_upper = metric.strip().upper()
        if metric_upper not in self.allowed_metrics:
            raise ValidationError(f"Unsupported metric '{metric}'. Allowed metrics are {self.allowed_metrics}.")

        # Validate column
        if column:
            if column != "*":
                if column not in schema_dict:
                    raise ValidationError(f"Column '{column}' does not exist in table '{table}' for aggregation.")
            col_expr = column
        else:
            if metric_upper == "COUNT":
                col_expr = "*"
            else:
                raise ValidationError(f"Column must be specified for metric '{metric_upper}'.")

        # Validate group_by
        group_by_cols = []
        if group_by:
            if isinstance(group_by, str):
                group_by_cols = [group_by]
            elif isinstance(group_by, list):
                group_by_cols = group_by
            else:
                raise ValidationError("Group_by must be a column name string or a list of column names.")

            # Validate each group_by column
            for col in group_by_cols:
                if col not in schema_dict:
                    raise ValidationError(f"Group by column '{col}' does not exist in table '{table}'.")

        # Build Select expressions
        select_exprs = []
        if group_by_cols:
            select_exprs.extend(group_by_cols)
        select_exprs.append(f"{metric_upper}({col_expr}) AS value")
        select_clause = ", ".join(select_exprs)

        # Build Group By clause
        if group_by_cols:
            group_by_clause = " GROUP BY " + ", ".join(group_by_cols)
        else:
            group_by_clause = ""

        # Parse filters
        where_clause, params = self._parse_filters(table, schema_dict, filters)

        # Build SQL safely
        sql = f"SELECT {select_clause} FROM {table}{where_clause}{group_by_clause};"

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
