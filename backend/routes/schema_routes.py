from flask import Blueprint, request, jsonify
from services.schema_service import (
    apply_schema,
    fetch_all_tables,
    fetch_table_details,
    fetch_current_schema
)

schema_bp = Blueprint('schema', __name__)

@schema_bp.route('/schema', methods=['POST'])
def handle_schema_endpoint():
    """
    Receives schema design from frontend.
    Compares with current DB state. Drops tables removed from canvas.
    Drops/Recreates tables present on canvas (destructive update).
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    schema_data = request.get_json()
    if not schema_data:
        return jsonify({"error": "No JSON data received"}), 400

    print("Received schema data:", schema_data)
    tables_from_canvas_data = schema_data.get('tables', [])
    relationships_data = schema_data.get('relationships', [])

    response, status_code = apply_schema(tables_from_canvas_data, relationships_data)
    return jsonify(response), status_code

@schema_bp.route('/tables', methods=['GET'])
def get_tables_endpoint():
    """Returns list of tables in the database."""
    data, error, status_code = fetch_all_tables()
    if error:
        return jsonify({"error": error}), status_code
    return jsonify(data), status_code

@schema_bp.route('/table_details/<table_name>', methods=['GET'])
def get_table_details_endpoint(table_name):
    """Returns column and attribute metadata for a specific table."""
    data, error, status_code = fetch_table_details(table_name)
    if error:
        return jsonify({"error": error}), status_code
    return jsonify(data), status_code

@schema_bp.route('/current_schema', methods=['GET'])
def get_current_schema_endpoint():
    """Fetches the current schema (tables, columns, foreign keys) from the database."""
    schema, error, status_code = fetch_current_schema()
    if error:
        return jsonify({"error": error}), status_code
    return jsonify(schema), status_code
