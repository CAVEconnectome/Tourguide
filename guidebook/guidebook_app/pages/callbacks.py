import flask
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from ..utils import make_client, stash_dataframe, rehydrate_dataframe
from ...guidebook_lib.processing import (
    process_meshwork_to_dataframe,
    add_downstream_column,
    update_seen_id_list,
)
from pcg_skel import get_meshwork_from_client, VERTEX_COLUMNS
import pandas as pd
import time
import os

VERTEX_LIST_COLS = ["lvl2_id"]

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


@callback(
    Output("vertex-df", "data"),
    Output("seen-lvl2_ids", "data"),
    Output("message-text", "children"),
    Output("message-text", "color"),
    Output("main-loading-placeholder", "children"),
    [
        State("guidebook-root-id", "value"),
        State("url", "pathname"),
        Input("submit-button", "n_clicks"),
        Input("seen-lvl2-ids", "data"),
    ],
    prevent_initial_call=True,
    running=[(Output("submit-button", "disabled"), True, False)],
)
def process_root_id(root_id, url, _):
    t0 = time.time()
    if root_id is None:
        vertex_df = pd.DataFrame(columns=VERTEX_COLUMNS)
        return (
            stash_dataframe(vertex_df),
            seen_lvl2_ids,
            "Please provide a Root ID",
            "warning",
            "",
        )
    client = make_client(
        get_datastack(url),
        server_address=os.environ.get("GUIDEBOOK_SERVER_ADDRESS"),
        auth_token=None,
    )
    print(flask.g)
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
            stash_dataframe(vertex_df),
            seen_lvl2_ids,
            message_text,
            message_color,
            "",
        )

    vertex_df = process_meshwork_to_dataframe(nrn)
    message_text = f"Successfully processed root ID {root_id} with {len(vertex_df)} vertices in {time.time() - t0:.2f} seconds"
    message_color = "success"
    return (
        stash_dataframe(vertex_df, list_cols=["lvl2_id"]),
        update_seen_id_list(seen_lvl2_ids, vertex_df),
        message_text,
        message_color,
        "",
    )

@callback(
    Output("end-point-link", "children"),
    Input("vertex-data", "data"),
    Input("end-point-link-button", "n_clicks"),
    prevent_initial_call=True,
):
def generate_end_point_link(vertex_data, _):
    if vertex_data is None:
        return ""
    vertex_df = pd.DataFrame(vertex_data)
    end_points = vertex_df.query("is_end_point")
    if len(end_points) == 0:
        return "No end points found"
    end_point_ids = end_points.index.values
    return html.A(
        f"View {len(end_points)} end points",
        href=f"/dash/guidebook-app/end-points?end_point_ids={','.join(end_point_ids)}",
    )