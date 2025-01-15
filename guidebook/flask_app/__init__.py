from flask import Flask
from .config import configure_app
from .api import api_bp
from ..guidebook_app import create_guidebook_app
import os

__version__ = "0.0.1"


def create_app():
    app = Flask(
        __name__,
    )
    app = configure_app(app)
    register_blueprints(app)
    with app.app_context():
        create_guidebook_app(
            "guidebook-app",
            server=app,
            url_base_pathname=os.environ.get("URL_PREFIX", "/dash/"),
        )
    return app


def register_blueprints(app: Flask):
    app.register_blueprint(api_bp, url_prefix="")
