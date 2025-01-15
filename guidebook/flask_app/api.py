from flask import Blueprint, render_template, g

api_bp = Blueprint("main", __name__)
__version__ = "0.0.1"


@api_bp.route("/")
def index():
    return render_template("index.html", title="Guidebook", version=__version__)
