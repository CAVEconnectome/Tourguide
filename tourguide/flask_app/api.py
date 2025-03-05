from flask import Blueprint, render_template, g
from .config import TOURGUIDE_PREFIX

api_bp = Blueprint("main", __name__)
__version__ = "2.1.0"


@api_bp.route("/")
def index():
    return render_template("index.html", title="TourGuide", version=__version__)


@api_bp.route("/version")
def version():
    return __version__
