from mysql.connector import Error
from config import DB_NAME
from database import get_db_connection
from utils.sanitizer import sanitize_identifier

def fetch_all_tables():
    """Fetches list of all table names from the database."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            return None, "Database connection failed", 500
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [table[0] for table in cursor.fetchall()]
        return {"tables": tables}, None, 200
    except Error as e:
        return None, f"Database error fetching tables: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def fetch_table_details(table_name):
    """Fetches column and constraint information for a specific table."""
    safe_table_name = sanitize_identifier(table_name)
    if not safe_table_name:
        return None, "Invalid table name provided", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            return None, "Database connection failed", 500
        cursor = conn.cursor(dictionary=True)
        describe_sql = f"DESCRIBE `{safe_table_name}`;"
        cursor.execute(describe_sql)
        columns_raw = cursor.fetchall()
        attributes = []
        for col in columns_raw:
            col_type_raw = col.get('Type', '').upper()
            col_type = col_type_raw
            if 'VARCHAR' in col_type_raw:
                col_type = 'VARCHAR(255)'
            elif 'TINYINT' in col_type_raw or 'BOOL' in col_type_raw:
                col_type = 'BOOLEAN'
            elif 'INT' in col_type_raw:
                col_type = 'INT'
            elif 'TEXT' in col_type_raw:
                col_type = 'TEXT'
            elif 'DATE' in col_type_raw:
                col_type = 'DATE'
            elif 'DECIMAL' in col_type_raw:
                col_type = 'DECIMAL(10,2)'
            attributes.append({
                "name": col.get('Field'),
                "type": col_type,
                "isPK": col.get('Key') == 'PRI',
                "isNotNull": col.get('Null') == 'NO',
                "isUnique": col.get('Key') == 'UNI',
            })
        return {"table_name": safe_table_name, "attributes": attributes}, None, 200
    except Error as e:
        if e.errno == 1146:
            return None, f"Table '{safe_table_name}' not found.", 404
        return None, f"Database error fetching table details: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def fetch_current_schema():
    """Fetches the current schema (tables, columns, foreign keys) from the database."""
    conn = None
    cursor = None
    schema = {'tables': {}, 'relationships': []}

    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            return None, "Database connection failed", 500

        cursor = conn.cursor(dictionary=True)
        db_name = DB_NAME

        # 1. Get Tables
        cursor.execute("SHOW TABLES;")
        tables_raw = cursor.fetchall()
        table_names = [t['Tables_in_' + db_name] for t in tables_raw]

        if not table_names:
            return schema, None, 200

        # 2. Get Columns and Constraints for each table
        for table_name in table_names:
            safe_table_name = sanitize_identifier(table_name)
            if not safe_table_name:
                continue

            cols_sql = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION;
            """
            cursor.execute(cols_sql, (db_name, table_name))
            columns_raw = cursor.fetchall()

            attributes = []
            for col in columns_raw:
                col_type_raw = col.get('DATA_TYPE', '').upper()
                col_type = col_type_raw
                if 'VARCHAR' in col_type_raw:
                    col_type = 'VARCHAR(255)'
                elif 'TINYINT' in col_type_raw or 'BOOL' in col_type_raw:
                    col_type = 'BOOLEAN'
                elif 'INT' in col_type_raw:
                    col_type = 'INT'
                elif 'TEXT' in col_type_raw:
                    col_type = 'TEXT'
                elif 'DATE' in col_type_raw:
                    col_type = 'DATE'
                elif 'DECIMAL' in col_type_raw:
                    col_type = 'DECIMAL(10,2)'
                attributes.append({
                    "name": col.get('COLUMN_NAME'),
                    "type": col_type,
                    "isPK": col.get('COLUMN_KEY') == 'PRI',
                    "isNotNull": col.get('IS_NULLABLE') == 'NO',
                    "isUnique": col.get('COLUMN_KEY') == 'UNI',
                })
            schema['tables'][table_name] = {"name": table_name, "attributes": attributes}

        # 3. Get Foreign Keys
        fks_sql = """
        SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_SCHEMA IS NOT NULL;
        """
        cursor.execute(fks_sql, (db_name,))
        fks_raw = cursor.fetchall()

        for fk in fks_raw:
            source_table = fk['TABLE_NAME']
            target_table = fk['REFERENCED_TABLE_NAME']
            if source_table in schema['tables'] and target_table in schema['tables']:
                schema['relationships'].append({
                    "id": f"fk-{fk['CONSTRAINT_NAME']}",
                    "source": source_table,
                    "target": target_table,
                })

        return schema, None, 200
    except Error as e:
        print(f"Error fetching current schema: {e}")
        return None, f"Database error fetching current schema: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def apply_schema(tables_from_canvas_data, relationships_data):
    """
    Receives schema design from frontend.
    Compares with current DB state. Drops tables removed from canvas.
    Drops/Recreates tables present on canvas (destructive update).
    Creates tables and foreign key constraints.
    """
    conn = None
    cursor = None
    created_tables_details = {}
    added_foreign_keys = []
    dropped_tables = []
    errors = {"fetching": [], "dropping": [], "table_creation": [], "fk_creation": []}

    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            return {"error": "Database connection failed"}, 500
        cursor = conn.cursor()

        # --- Phase 0a: Get existing tables from DB ---
        existing_db_tables = set()
        try:
            cursor.execute("SHOW TABLES;")
            for (table_name,) in cursor.fetchall():
                existing_db_tables.add(table_name)
        except Error as e:
            errors["fetching"].append(f"Error fetching existing tables: {e}")
            raise Exception("Failed to fetch existing tables.")

        # --- Phase 0b: Identify tables to drop (in DB but not on canvas) ---
        tables_on_canvas_safe_names = {sanitize_identifier(t.get('name')) for t in tables_from_canvas_data if t.get('name')}
        tables_to_explicitly_drop = existing_db_tables - tables_on_canvas_safe_names

        # --- Phase 0c: Drop tables ---
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

        # Drop tables removed from canvas
        for table_to_drop in reversed(list(tables_to_explicitly_drop)):
            try:
                drop_sql = f"DROP TABLE IF EXISTS `{table_to_drop}`;"
                cursor.execute(drop_sql)
                dropped_tables.append(table_to_drop)
            except Error as drop_error:
                errors["dropping"].append({"table_name": table_to_drop, "error": str(drop_error)})

        # Drop tables that ARE on the canvas (for recreation)
        tables_to_recreate_safe_names = list(tables_on_canvas_safe_names)
        for safe_table_name in reversed(tables_to_recreate_safe_names):
            try:
                if safe_table_name in existing_db_tables:
                    drop_sql = f"DROP TABLE IF EXISTS `{safe_table_name}`;"
                    cursor.execute(drop_sql)
            except Error as drop_error:
                errors["dropping"].append({"table_name": safe_table_name, "warning": f"Error during recreation drop: {drop_error}"})

        conn.commit()

        # --- Phase 1: Create Tables ---
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

        node_id_to_safe_name = {}
        for table_info in tables_from_canvas_data:
            original_table_name = table_info.get('name')
            node_id = table_info.get('id')
            attributes = table_info.get('attributes', [])
            safe_table_name = sanitize_identifier(original_table_name)

            if not safe_table_name or not node_id:
                errors["table_creation"].append({"table_info": table_info, "error": "Missing table name or node ID"})
                continue
            if not attributes:
                errors["table_creation"].append({"table_name": safe_table_name, "error": "Table has no attributes defined"})
                continue

            column_definitions = []
            primary_keys = []
            for attr in attributes:
                col_name = sanitize_identifier(attr.get('name'))
                col_type = attr.get('type', 'VARCHAR(255)')
                if col_type.upper() not in ['INT', 'VARCHAR(255)', 'TEXT', 'DATE', 'BOOLEAN', 'DECIMAL(10,2)']:
                    col_type = 'VARCHAR(255)'
                if not col_name:
                    errors["table_creation"].append({"table_name": safe_table_name, "error": f"Attribute missing name: {attr}"})
                    continue

                col_def_parts = [f"`{col_name}`", col_type]
                if attr.get('isNotNull', False):
                    col_def_parts.append("NOT NULL")
                if attr.get('isUnique', False):
                    col_def_parts.append("UNIQUE")
                column_definitions.append(" ".join(col_def_parts))
                if attr.get('isPK', False):
                    primary_keys.append(f"`{col_name}`")

            if not column_definitions:
                errors["table_creation"].append({"table_name": safe_table_name, "error": "No valid column definitions generated"})
                continue

            sql = f"CREATE TABLE `{safe_table_name}` (\n"
            sql += ",\n".join(f"    {col_def}" for col_def in column_definitions)
            if primary_keys:
                sql += f",\n    PRIMARY KEY ({', '.join(primary_keys)})"
            sql += "\n);"

            try:
                cursor.execute(sql)
                node_id_to_safe_name[node_id] = safe_table_name
                created_tables_details[safe_table_name] = {"table_name": safe_table_name, "attributes": attributes}
            except Error as table_error:
                errors["table_creation"].append({"table_name": safe_table_name, "sql": sql, "error": str(table_error)})

        if not errors["table_creation"]:
            conn.commit()
        else:
            conn.rollback()
            raise Exception("Table creation failed, cannot proceed to FKs.")

        # --- Phase 2: Add Foreign Keys ---
        for fk_info in relationships_data:
            source_node_id = fk_info.get('sourceTableId')
            target_node_id = fk_info.get('targetTableId')

            source_table_name = node_id_to_safe_name.get(source_node_id)
            target_table_name = node_id_to_safe_name.get(target_node_id)

            if not source_table_name or not target_table_name:
                errors["fk_creation"].append({
                    "fk_info": fk_info,
                    "error": f"Could not map source ({source_node_id}) or target ({target_node_id}) node ID to created table name"
                })
                continue

            target_pk_col = 'id'
            target_table_data = next((t for t in tables_from_canvas_data if t.get('id') == target_node_id), None)
            if target_table_data:
                pk_attr = next((a for a in target_table_data.get('attributes', []) if a.get('isPK')), None)
                if pk_attr:
                    target_pk_col = sanitize_identifier(pk_attr.get('name', 'id'))

            fk_col_name = sanitize_identifier(f"{target_table_name}_{target_pk_col}")
            fk_col_type = 'INT'

            sql_add_col = f"ALTER TABLE `{source_table_name}` ADD COLUMN `{fk_col_name}` {fk_col_type};"
            constraint_name = sanitize_identifier(f"fk_{source_table_name}_{target_table_name}_{fk_col_name}")
            sql_add_fk = f"""
            ALTER TABLE `{source_table_name}`
            ADD CONSTRAINT `{constraint_name}`
            FOREIGN KEY (`{fk_col_name}`)
            REFERENCES `{target_table_name}` (`{target_pk_col}`);
            """
            try:
                cursor.execute(sql_add_col)
                cursor.execute(sql_add_fk)
                added_foreign_keys.append({
                    "source_table": source_table_name,
                    "fk_column": fk_col_name,
                    "target_table": target_table_name,
                    "target_pk_column": target_pk_col,
                    "constraint_name": constraint_name
                })
            except Error as fk_error:
                if fk_error.errno == 1060: # Duplicate column
                    try:
                        cursor.execute(sql_add_fk)
                        added_foreign_keys.append({
                            "source_table": source_table_name,
                            "fk_column": fk_col_name,
                            "target_table": target_table_name,
                            "target_pk_column": target_pk_col,
                            "constraint_name": constraint_name
                        })
                    except Error as fk_constraint_error:
                        errors["fk_creation"].append({
                            "source_table": source_table_name,
                            "target_table": target_table_name,
                            "error": f"Failed ADD CONSTRAINT after column existed: {fk_constraint_error}"
                        })
                elif fk_error.errno == 1061: # Duplicate key name
                    pass
                elif fk_error.errno == 1822: # Failed adding foreign key constraint
                    errors["fk_creation"].append({
                        "source_table": source_table_name,
                        "target_table": target_table_name,
                        "error": f"Failed adding FK constraint '{constraint_name}': {fk_error}"
                    })
                else:
                    errors["fk_creation"].append({
                        "source_table": source_table_name,
                        "target_table": target_table_name,
                        "sql_add_col": sql_add_col,
                        "sql_add_fk": sql_add_fk,
                        "error": str(fk_error)
                    })

        conn.commit()

    except Exception as e:
        print(f"Error during schema handling: {e}")
        if "table_creation" not in errors: errors["table_creation"] = []
        if "fk_creation" not in errors: errors["fk_creation"] = []
        if "dropping" not in errors: errors["dropping"] = []
        if "fetching" not in errors: errors["fetching"] = []
        errors["general"] = str(e)
        if conn:
            conn.rollback()
    finally:
        if cursor:
            try:
                cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            except Error as fk_check_error:
                print(f"Warning: Could not re-enable FK checks: {fk_check_error}")
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    final_message = "Schema processing attempted."
    has_errors = any(errors.get(k) for k in errors if k != 'general') or errors.get("general")
    has_success = created_tables_details or added_foreign_keys or dropped_tables

    if not has_errors:
        final_message = "Schema applied successfully."
    elif has_success:
        final_message = "Schema applied with errors/warnings."

    response = {
        "message": final_message,
        "created_tables": list(created_tables_details.values()),
        "dropped_tables": dropped_tables,
        "added_foreign_keys": added_foreign_keys,
        "errors": errors
    }
    status_code = 200 if not has_errors else (207 if has_success else 400)
    return response, status_code
