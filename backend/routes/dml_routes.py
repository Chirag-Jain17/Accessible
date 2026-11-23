from flask import Blueprint, request, jsonify
from services.dml_service import execute_dml

dml_bp = Blueprint('dml', __name__)

@dml_bp.route('/execute_dml', methods=['POST'])
def execute_dml_statement_endpoint():
    """Executes INSERT, UPDATE, or DELETE operations with parameterized queries."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "No JSON data received"}), 400

    print(f"Received DML payload: {payload}")
    response, status_code = execute_dml(payload)
    return jsonify(response), status_code
