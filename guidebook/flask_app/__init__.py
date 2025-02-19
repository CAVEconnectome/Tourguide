from flask import Flask
from .config import configure_app, protect_app
from .api import api_bp
from ..guidebook_app import create_guidebook_app
import os

meta_viewport = {
    "name": "viewport",
    "content": "width=device-width, initial-scale=1, shrink-to-fit=no",
}

url_prefix = os.environ.get("GUIDEBOOK_APP_URL_PREFIX", "/app/")


def create_app():
    app = Flask(
        __name__,
    )
    configure_app(app)
    register_blueprints(app)
    with app.app_context():
        dapp = create_guidebook_app(
            "guidebook-app",
            server=app,
            url_base_pathname=url_prefix,
            meta_tags=[meta_viewport],
        )
    protect_app(dapp)
    return app


def register_blueprints(app: Flask):
    app.register_blueprint(api_bp, url_prefix="")
