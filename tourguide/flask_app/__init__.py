from flask import Flask
from .config import configure_app, protect_app, TOURGUIDE_PREFIX
from .api import api_bp
from ..tourguide_app import create_tourguide_app
import os

meta_viewport = {
    "name": "viewport",
    "content": "width=device-width, initial-scale=1, shrink-to-fit=no",
}

url_prefix = f"{TOURGUIDE_PREFIX}/{os.environ.get('TOURGUIDE_APP_URL_PREFIX', 'app/')}"


def create_app():
    app = Flask(
        __name__,
    )
    configure_app(app)
    register_blueprints(app)
    with app.app_context():
        dapp = create_tourguide_app(
            "tourguide-app",
            server=app,
            url_base_pathname=url_prefix,
            meta_tags=[meta_viewport],
        )
    protect_app(dapp)
    return app


def register_blueprints(app: Flask):
    app.register_blueprint(api_bp, url_prefix=TOURGUIDE_PREFIX)
