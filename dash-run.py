import dash
from dash import Dash
import dash_mantine_components as dmc

from tourguide.tourguide_app.external_stylesheets import external_stylesheets
from tourguide.tourguide_app.pages.callbacks import register_callbacks
import pathlib

pages_folder = (
    pathlib.Path(__file__).parent.absolute().joinpath("tourguide/tourguide_app/pages")
)

dapp = Dash(
    name="dashtest",
    use_pages=True,
    pages_folder=pages_folder,
    external_stylesheets=dmc.styles.ALL,
)
register_callbacks(dapp)

if __name__ == "__main__":
    dapp.run_server(
        host="0.0.0.0",
        port=8008,
        debug=True,
        threaded=True,
    )
