from flask import Flask
from app.config import load_configurations, configure_logging
from app.services.combined_openai_service import initialize_openai_client
from .views import webhook_blueprint


def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Initialize services that depend on app.config
    initialize_openai_client()

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)

    return app
