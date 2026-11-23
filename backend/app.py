import os
import sys

# Ensure backend directory is in sys.path so modules can be imported
# whether started from backend directory or project root
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask
from flask_cors import CORS
from config import SERVER_HOST, SERVER_PORT, DEBUG_MODE
from routes import register_routes

def create_app():
    """Application factory for initializing the Flask app."""
    app = Flask(__name__)
    
    # Enable CORS for frontend requests
    CORS(app)
    
    # Register all modular blueprint routes
    register_routes(app)
    
    return app

# Module-level app instance for WSGI / direct execution
app = create_app()

if __name__ == '__main__':
    print(f"Starting server on {SERVER_HOST}:{SERVER_PORT} (debug={DEBUG_MODE})...")
    app.run(host=SERVER_HOST, debug=DEBUG_MODE, port=SERVER_PORT)
