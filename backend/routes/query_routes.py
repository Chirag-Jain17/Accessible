from flask import Blueprint, request, jsonify
from services.query_service import execute_select

query_bp = Blueprint('query', __name__)

@query_bp.route('/execute_select', methods=['POST'])
def execute_select_query_endpoint():
    """Executes a dynamic SELECT query defined by the frontend."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    query_def = request.get_json()
    if not query_def:
        return jsonify({"error": "No JSON data received"}), 400

    print(f"Received query definition: {query_def}")
    response, status_code = execute_select(query_def)
    return jsonify(response), status_code
