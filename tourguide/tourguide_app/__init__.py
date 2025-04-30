import flask
from dash import Dash

import dash_mantine_components as dmc

from .pages.callbacks import register_callbacks
import pathlib

pages_folder = pathlib.Path(__file__).parent.absolute().joinpath("pages")


def create_tourguide_app(name=__name__, config={}, **kwargs):
    dapp = Dash(
        name,
        use_pages=True,
        pages_folder=pages_folder,
        **kwargs,
    )
    register_callbacks(dapp)

    return dapp
