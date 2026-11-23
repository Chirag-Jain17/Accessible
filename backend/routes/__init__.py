from .general_routes import general_bp
from .schema_routes import schema_bp
from .query_routes import query_bp
from .dml_routes import dml_bp
from .normalization_routes import normalization_bp

def register_routes(app):
    """Registers all API blueprints on the Flask application."""
    app.register_blueprint(general_bp, url_prefix='/api')
    app.register_blueprint(schema_bp, url_prefix='/api')
    app.register_blueprint(query_bp, url_prefix='/api')
    app.register_blueprint(dml_bp, url_prefix='/api')
    app.register_blueprint(normalization_bp, url_prefix='/api')
