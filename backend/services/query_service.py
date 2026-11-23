from mysql.connector import Error
from config import ALLOWED_AGGREGATES, ALLOWED_JOIN_TYPES
from database import get_db_connection
from utils.sanitizer import sanitize_identifier
from utils.query_builder import build_where_clause

def execute_select(query_def):
    """
    Constructs and executes a dynamic SELECT query with joins, where filters,
    aggregates, and group by clauses.
    """
    select_parts = query_def.get('select', [])
    from_tables = query_def.get('from', [])
    join_conditions = query_def.get('joins', [])
    where_conditions = query_def.get('where', [])
    group_by_columns = query_def.get('groupBy', [])

    if not from_tables:
        return {"error": "Query must specify at least one table in 'from'"}, 400
    if not select_parts:
        return {"error": "Query must specify columns or aggregates in 'select'"}, 400

    if len(from_tables) > 1 and not join_conditions:
        return {"error": f"Multiple tables ({', '.join(from_tables)}) selected. Please define JOIN conditions between them."}, 400

    sql_parts = []
    params = []

    # --- 1. Build SELECT Clause ---
    select_clause_items = []
    has_aggregates = any(p.get('type') == 'aggregate' for p in select_parts)
    tables_in_select = set()

    for item in select_parts:
        item_type = item.get('type')
        table = sanitize_identifier(item.get('table'))
        column = item.get('column')
        tables_in_select.add(table)

        if item_type == 'column':
            safe_column = sanitize_identifier(column)
            if not safe_column:
                return {"error": f"Missing or invalid column name: {item}"}, 400
            qualify = len(from_tables) > 1
            select_clause_items.append(f"`{table}`.`{safe_column}`" if qualify else f"`{safe_column}`")
        elif item_type == 'aggregate':
            func = str(item.get('func', '')).upper()
            alias = sanitize_identifier(item.get('alias'))
            if func not in ALLOWED_AGGREGATES:
                return {"error": f"Invalid aggregate func: {func}"}, 400
            if not column:
                return {"error": f"Missing column for aggregate {func}"}, 400
            target_col = f"`{sanitize_identifier(column)}`" if column != '*' else '*'
            if column == '*' and func != 'COUNT':
                return {"error": "'*' only allowed with COUNT"}, 400
            if column != '*' and not sanitize_identifier(column):
                return {"error": f"Invalid col name for aggregate {func}: {column}"}, 400
            qualify = len(from_tables) > 1
            agg_target = f"`{table}`.{target_col}" if qualify and column != '*' else target_col
            agg_str = f"{func}({agg_target})"
            if alias:
                agg_str += f" AS `{alias}`"
            select_clause_items.append(agg_str)
        else:
            return {"error": f"Unknown select item type: {item_type}"}, 400

    sql_parts.append(f"SELECT {', '.join(select_clause_items)}")

    # --- 2. Build FROM and JOIN Clauses ---
    first_table = sanitize_identifier(from_tables[0])
    if not first_table:
        return {"error": "Invalid first table name"}, 400
    sql_parts.append(f"FROM `{first_table}`")

    tables_in_query = {first_table}
    joined_tables = set()
    for join in join_conditions:
        join_type = str(join.get('type', 'INNER')).upper()
        left_table = sanitize_identifier(join.get('leftTable'))
        left_col = sanitize_identifier(join.get('leftCol'))
        right_table = sanitize_identifier(join.get('rightTable'))
        right_col = sanitize_identifier(join.get('rightCol'))

        if join_type not in ALLOWED_JOIN_TYPES:
            return {"error": f"Invalid join type: {join_type}"}, 400
        if not (left_table and left_col and right_table and right_col):
            return {"error": f"Incomplete join definition: {join}"}, 400

        if left_table not in from_tables or right_table not in from_tables:
            return {"error": f"JOIN involves table(s) not selected in the 'FROM' list: {left_table}, {right_table}"}, 400

        sql_parts.append(f"{join_type} JOIN `{right_table}` ON `{left_table}`.`{left_col}` = `{right_table}`.`{right_col}`")
        tables_in_query.add(right_table)
        joined_tables.add(left_table)
        joined_tables.add(right_table)

    if len(from_tables) > 1:
        unjoined_tables = set(from_tables) - tables_in_query
        if unjoined_tables:
            return {"error": f"Table(s) '{', '.join(unjoined_tables)}' selected but not included in any JOIN condition."}, 400

    select_tables_not_in_query = tables_in_select - tables_in_query
    if select_tables_not_in_query:
        return {"error": f"SELECT list uses columns from table(s) '{', '.join(select_tables_not_in_query)}' which are not in FROM or JOIN clauses."}, 400

    # --- 3. Build WHERE Clause ---
    if where_conditions:
        try:
            where_clause_sql, where_params = build_where_clause(where_conditions)
            if where_clause_sql:
                sql_parts.append(f"WHERE {where_clause_sql}")
                params.extend(where_params)
        except ValueError as ve:
            return {"error": f"Invalid WHERE clause: {ve}"}, 400

    # --- 4. Build GROUP BY Clause ---
    if group_by_columns:
        group_by_clause_items = []
        allowed_group_by_cols = {f"{sanitize_identifier(p.get('table'))}.{sanitize_identifier(p.get('column'))}" for p in select_parts if p.get('type') == 'column'}
        for col_ref in group_by_columns:
            parts = col_ref.split('.', 1)
            table = sanitize_identifier(parts[0])
            column = sanitize_identifier(parts[1])
            safe_qualified_col = f"`{table}`.`{column}`"
            internal_ref = f"{table}.{column}"
            if not (table and column):
                return {"error": f"Invalid GROUP BY format: {col_ref}"}, 400
            if table not in tables_in_query:
                return {"error": f"GROUP BY col '{col_ref}' uses table not in query"}, 400
            if internal_ref not in allowed_group_by_cols and has_aggregates:
                return {"error": f"GROUP BY column '{col_ref}' must be in non-aggregated SELECT list"}, 400
            group_by_clause_items.append(safe_qualified_col)
        if group_by_clause_items:
            sql_parts.append(f"GROUP BY {', '.join(group_by_clause_items)}")

    # --- Combine and Execute ---
    final_sql = "\n".join(sql_parts) + ";"
    print(f"--- Generated SQL ---\n{final_sql}\nParameters: {params}\n---------------------")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            return {"error": "Database connection failed"}, 500
        cursor = conn.cursor()
        cursor.execute(final_sql, params)
        results_tuples = cursor.fetchall()
        column_names = cursor.column_names
        return {"columns": column_names, "rows": results_tuples}, 200

    except Error as e:
        print(f"Database Error executing query: {e}")
        error_msg = f"Database error: {e.msg}" if hasattr(e, 'msg') else f"Database error: {e}"
        if hasattr(e, 'errno'):
            if e.errno == 1054:
                error_msg = f"Database error: Unknown column specified. Check spelling/tables. (Details: {e.msg})"
            elif e.errno == 1146:
                error_msg = f"Database error: Table does not exist. (Details: {e.msg})"
            elif e.errno == 1064:
                error_msg = f"Database error: Syntax error in SQL. Check query builder logic. (Details: {e.msg})"
        return {"error": error_msg, "sql_attempted": final_sql}, 500
    except Exception as ex:
        print(f"Unexpected Error executing query: {ex}")
        return {"error": f"An unexpected server error occurred: {ex}"}, 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
