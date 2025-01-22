import flask
import dash
from dash import Dash, _dash_renderer

# Required for dash mantine components
_dash_renderer._set_react_version("18.2.0")

import dash_mantine_components as dmc

from .external_stylesheets import external_stylesheets
from .pages.callbacks import register_callbacks
import pathlib
import os

pages_folder = pathlib.Path(__file__).parent.absolute().joinpath("pages")


def create_guidebook_app(name=__name__, config={}, **kwargs):
    dapp = Dash(
        name,
        use_pages=True,
        external_stylesheets=dmc.styles.ALL,
        pages_folder=pages_folder,
        **kwargs,
    )
    register_callbacks(dapp)

    return dapp
