from flask import Blueprint, render_template, g

api_bp = Blueprint("main", __name__)
__version__ = "2.0.2"


@api_bp.route("/")
def index():
    return render_template("index.html", title="Guidebook", version=__version__)


@api_bp.route("/version")
def version():
    return __version__
