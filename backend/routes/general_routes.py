from flask import Blueprint, jsonify
from mysql.connector import Error
from database import get_db_connection

general_bp = Blueprint('general', __name__)

@general_bp.route('/ping', methods=['GET'])
def ping_pong():
    """Health check endpoint."""
    return jsonify(message='pong!')

@general_bp.route('/db_test', methods=['GET'])
def test_db():
    """Database connection test endpoint."""
    conn = None
    try:
        conn = get_db_connection()
        if conn and conn.is_connected():
            db_info = conn.get_server_info()
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            cursor.close()
            return jsonify(
                message="Database connection successful!",
                server_info=db_info,
                database=record[0]
            ), 200
        else:
            return jsonify(error="Database connection failed."), 500
    except Error as e:
        return jsonify(error=f"Database connection error: {e}"), 500
    finally:
        if conn and conn.is_connected():
            conn.close()
