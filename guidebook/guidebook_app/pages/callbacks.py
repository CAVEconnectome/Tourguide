from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from ..utils import make_client
from pcg_skel import get_meshwork_from_client
import pandas as pd

VERTEX_COLUMNS = ["pt_position"]


def get_datastack(pathname):
    if pathname is not None:
        return pathname.split("/")[-1]
    else:
        return None


@callback(Output("header-bar", "children"), Input("url", "pathname"))
def set_header_text(url):
    return html.H3(
        f"Guidebook — {get_datastack(url)}",
        className="bg-primary text-white p-2 mb-2 text-center",
    )


# @callback(
#     Output("message-text", "children"),
#     [
#         State("guidebook-root-id", "value"),
#         State("url", "pathname"),
#         Input("submit-button", "n_clicks"),
#     ],
# )
# def message_text(root_id, url, _):
#     return f"""Datastack: {get_datastack(url)}\nRoot ID: {root_id}"""


@callback(
    Output("vertices", "data"),
    Output("message-text", "children"),
    Output("message-text", "color"),
    [
        State("guidebook-root-id", "value"),
        State("url", "pathname"),
        Input("submit-button", "n_clicks"),
    ],
    prevent_initial_call=True,
    running=[(Output("submit-button", "disabled"), True, False)],
)
def process_root_id(root_id, url, _):
    if root_id is None:
        vertex_df = pd.DataFrame(columns=VERTEX_COLUMNS)
        return (vertex_df.to_dict("records"), "Please provide a Root ID", "warning")
    client = make_client(get_datastack(url), server_address=None, auth_token=None)
    try:
        nrn = get_meshwork_from_client(
            int(root_id),
            client=client,
            synapses=False,
        )
    except Exception as e:
        vertex_df = pd.DataFrame(columns=VERTEX_COLUMNS)
        message_text = str(e)
        message_color = "danger"
        return (
            vertex_df.to_dict("records"),
            message_text,
            message_color,
        )

    vertex_df = pd.DataFrame({VERTEX_COLUMNS[0]: nrn.skeleton.vertices.tolist()})
    print(vertex_df)
    message_text = f"Stored {len(vertex_df)} vertices for root id {root_id}"
    message_color = "success"
    return vertex_df.to_dict("records"), message_text, message_color
