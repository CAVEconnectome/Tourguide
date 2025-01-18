import flask
import dash
from dash import Dash

from .external_stylesheets import external_stylesheets
from .pages.callbacks import register_callbacks
import pathlib
import os

pages_folder = pathlib.Path(__file__).parent.absolute().joinpath("pages")


def create_guidebook_app(name=__name__, config={}, **kwargs):
    if "external_stylesheets" not in kwargs:
        kwargs["external_stylesheets"] = external_stylesheets
    dapp = Dash(
        name,
        use_pages=True,
        pages_folder=pages_folder,
        **kwargs,
    )
    register_callbacks(dapp)

    return dapp
