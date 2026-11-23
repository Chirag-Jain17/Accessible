from mysql.connector import Error
from database import get_db_connection
from utils.sanitizer import sanitize_identifier
from utils.query_builder import build_where_clause

def execute_dml(payload):
    """
    Executes INSERT (multi-row), UPDATE, or DELETE statements based on frontend request.
    Uses parameterized queries for values.
    Generates WHERE clause dynamically for UPDATE/DELETE.
    """
    operation = str(payload.get('operation', '')).upper()
    table_name = sanitize_identifier(payload.get('table'))
    values_data = payload.get('values')
    set_data = payload.get('set', {})
    where_conditions = payload.get('where', [])

    if not table_name:
        return {"error": "Missing table name"}, 400

    conn = None
    cursor = None
    sql = ""
    params = []

    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            return {"error": "Database connection failed"}, 500
        cursor = conn.cursor()

        if operation == 'INSERT':
            if not values_data or not isinstance(values_data, list) or len(values_data) == 0:
                return {"error": "Missing or invalid 'values' list for INSERT operation"}, 400

            first_row = values_data[0]
            columns = [sanitize_identifier(col) for col in first_row.keys()]
            if not all(columns):
                return {"error": "Invalid column name(s) provided for INSERT"}, 400

            placeholders = ['%s'] * len(columns)
            sql = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in columns])}) VALUES ({', '.join(placeholders)});"

            params_list_of_tuples = []
            for row_dict in values_data:
                row_values = [row_dict.get(col) for col in columns]
                params_list_of_tuples.append(tuple(row_values))

            params = params_list_of_tuples

        elif operation == 'UPDATE':
            if not set_data:
                return {"error": "Missing SET data for UPDATE"}, 400
            if not where_conditions:
                return {"error": "Missing WHERE conditions for UPDATE"}, 400
            try:
                where_clause_sql, where_params = build_where_clause(where_conditions)
                if not where_clause_sql:
                    raise ValueError("Valid WHERE conditions are required for UPDATE.")
            except ValueError as ve:
                return {"error": f"Invalid WHERE clause: {ve}"}, 400

            set_clauses = []
            set_values = []
            for col, val in set_data.items():
                safe_col = sanitize_identifier(col)
                if not safe_col:
                    return {"error": f"Invalid column name in SET: {col}"}, 400
                set_clauses.append(f"`{safe_col}` = %s")
                set_values.append(val)

            sql = f"UPDATE `{table_name}` SET {', '.join(set_clauses)} WHERE {where_clause_sql};"
            params = set_values + where_params

        elif operation == 'DELETE':
            if not where_conditions:
                return {"error": "Missing WHERE conditions for DELETE"}, 400
            try:
                where_clause_sql, where_params = build_where_clause(where_conditions)
                if not where_clause_sql:
                    raise ValueError("Valid WHERE conditions are required for DELETE.")
            except ValueError as ve:
                return {"error": f"Invalid WHERE clause: {ve}"}, 400

            sql = f"DELETE FROM `{table_name}` WHERE {where_clause_sql};"
            params = where_params
        else:
            return {"error": f"Unsupported DML operation: {operation}"}, 400

        print(f"--- Generated DML ---\n{sql}\nParameters: {params}\n---------------------")

        if operation == 'INSERT':
            cursor.executemany(sql, params)
        else:
            cursor.execute(sql, params)

        conn.commit()

        affected_rows = cursor.rowcount
        message = f"{operation} successful. Rows affected: {affected_rows}"
        if (operation == 'UPDATE' or operation == 'DELETE') and affected_rows == 0:
            message = f"{operation} executed, but no rows matched the WHERE condition(s)."

        return {"message": message, "affectedRows": affected_rows}, 200

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Database Error executing DML: {e}")
        error_msg = f"Database error: {e.msg}" if hasattr(e, 'msg') else f"Database error: {e}"
        return {"error": error_msg, "sql_attempted": sql}, 500
    except ValueError as ve:
        if conn:
            conn.rollback()
        return {"error": f"Invalid WHERE condition: {ve}"}, 400
    except Exception as ex:
        if conn:
            conn.rollback()
        print(f"Unexpected Error executing DML: {ex}")
        return {"error": f"An unexpected server error occurred: {ex}"}, 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
