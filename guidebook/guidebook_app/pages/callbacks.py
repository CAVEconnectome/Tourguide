from typing import Optional
import flask
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_mantine_components as dmc
from ..utils import make_client, stash_dataframe, rehydrate_dataframe, link_maker_button
from ...guidebook_lib.processing import (
    process_meshwork_to_dataframe,
    add_downstream_column,
    update_seen_id_list,
    VERTEX_COLUMNS,
)
from ...guidebook_lib import states
from pcg_skel import get_meshwork_from_client
import pandas as pd
import time
import os

VERTEX_LIST_COLS = ["lvl2_id"]

axon_query_filter = "is_axon == True"
dendrite_query_filter = "is_axon == False"


def get_datastack(pathname):
    if pathname is not None:
        return pathname.split("/")[-1]
    else:
        return None


def register_callbacks(app):
    @app.callback(Output("header-bar", "children"), Input("url", "pathname"))
    def set_header_text(url):
        return html.H2(
            f"Guidebook — {get_datastack(url)}",
            className="text-center",
        )

    # Get offset between browser time and UTC time.
    app.clientside_callback(
        """function n(d) {
            const dt = new Date();
            return dt.getTimezoneOffset()
        }""",
        Output("timezone-offset", "data"),
        Input("load-interval", "n_intervals"),
    )

    @app.callback(
        Output("curr-root-id", "data"),
        Output("vertex-df", "data"),
        Output("seen-lvl2-ids", "data"),
        Output("message-text", "children"),
        Output("message-text", "color"),
        Output("end-point-link-button", "disabled"),
        Output("radio-axon", "disabled"),
        Output("radio-dendrite", "disabled"),
        [
            State("guidebook-root-id", "value"),
            State("url", "pathname"),
            Input("submit-button", "n_clicks"),
            State("seen-lvl2-ids", "data"),
        ],
        prevent_initial_call=True,
        running=[(Output("submit-button", "loading"), True, False)],
    )
    def process_root_id(root_id, url, _, seen_lvl2_ids):
        t0 = time.time()
        if root_id is None:
            vertex_df = pd.DataFrame(columns=VERTEX_COLUMNS)
            return (
                None,
                stash_dataframe(vertex_df),
                seen_lvl2_ids,
                "Please provide a Root ID",
                "yellow",
                True,
                True,
                True,
            )
        client = make_client(
            get_datastack(url),
            server_address=os.environ.get("GUIDEBOOK_SERVER_ADDRESS"),
            auth_token=None,
        )
        try:
            nrn = get_meshwork_from_client(
                int(root_id),
                client=client,
                synapses=False,
            )
        except Exception as e:
            vertex_df = pd.DataFrame(columns=VERTEX_COLUMNS)
            message_text = str(e)
            message_color = "red"
            return (
                None,
                stash_dataframe(vertex_df),
                seen_lvl2_ids,
                message_text,
                message_color,
                True,
                True,
                True,
            )

        vertex_df = process_meshwork_to_dataframe(nrn)
        disable_compartments = vertex_df["is_axon"].nunique() == 1
        message_text = f"Pre-processed root ID {root_id} with {len(vertex_df)} vertices in {time.time() - t0:.2f} seconds."
        message_color = "green"
        return (
            str(root_id),
            stash_dataframe(vertex_df, list_cols=["lvl2_id"]),
            update_seen_id_list(seen_lvl2_ids, vertex_df),
            message_text,
            message_color,
            False,
            disable_compartments,
            disable_compartments,
        )

    @app.callback(
        Output("end-point-link-card", "children"),
        State("curr-root-id", "data"),
        State("vertex-df", "data"),
        State("url", "pathname"),
        Input("compartment-radio", "value"),
        Input("end-point-link-button", "n_clicks"),
        prevent_initial_call=True,
        running=[(Output("end-point-link-button", "loading"), True, False)],
    )
    def generate_end_point_link(root_id, vertex_data, url_path, compartment_filter, _):
        end_point_default = (
            link_maker_button(
                "Generate End Point Link",
                button_id="end-point-link-button",
            ),
        )
        if ctx.triggered_id == "compartment-radio":
            return end_point_default

        if root_id is None or root_id == "" or vertex_data is None or vertex_data == []:
            return end_point_default
        datastack_name = get_datastack(url_path)
        vertex_df = pd.DataFrame(vertex_data)

        if compartment_filter == "axon":
            vertex_df = vertex_df.query(axon_query_filter)
        elif compartment_filter == "dendrite":
            vertex_df = vertex_df.query(dendrite_query_filter)

        client = make_client(
            datastack_name=datastack_name,
            server_address=os.environ.get("GUIDEBOOK_SERVER_ADDRESS"),
            auth_token=None,
        )
        url = states.end_point_link(int(root_id), vertex_df, client)
        return link_maker_button(
            "End Point Link",
            button_id="end-point-link-button",
            url=url,
        )

    @app.callback(
        Output("restriction-datetime", "disabled"),
        Input("use-time-restriction", "checked"),
    )
    def toggle_time_restrictions(value):
        return not value
