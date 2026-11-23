from flask import Blueprint, request, jsonify
from services.normalization_service import analyze_normalization

normalization_bp = Blueprint('normalization', __name__)

@normalization_bp.route('/analyze_normalization', methods=['POST'])
def analyze_normalization_endpoint():
    """Performs 1NF, 2NF, 3NF, BCNF analysis for a designated table and functional dependencies."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "No JSON data received"}), 400

    table_name = payload.get('table')
    user_fds_raw = payload.get('fds', [])

    if not table_name:
        return jsonify({"error": "Missing table name"}), 400

    response, status_code = analyze_normalization(table_name, user_fds_raw)
    return jsonify(response), status_code
