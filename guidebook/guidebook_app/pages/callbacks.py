from typing import Optional
import flask
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_mantine_components as dmc
from ..utils import (
    stash_dataframe,
    rehydrate_dataframe,
    link_maker_button,
    rehydrate_id_list,
    update_seen_id_list,
    convert_time_string_to_utc,
)
from ...guidebook_lib.processing import (
    process_meshwork_to_dataframe,
    filter_dataframe,
    process_new_points,
    VERTEX_COLUMNS,
    END_POINT_COLUMN,
    BRANCH_GROUP_COLUMN,
)
from ...guidebook_lib import states, lib_utils
from pcg_skel import get_meshwork_from_client
import pandas as pd
import time
import os

VERTEX_LIST_COLS = ["lvl2_id"]


def get_datastack(pathname):
    if pathname is not None:
        return pathname.split("/")[-1]
    else:
        return None


def link_process_generic(
    point_name,
    button_id,
    url_function,
    default_button,
    trigger_id,
    root_id,
    vertex_data,
    url_path,
    compartment_filter,
    point_filter,
    restriction_point,
    only_new_lvl2,
    only_after_timestamp,
    horizon_timestamp,
):
    if (
        trigger_id == "compartment-radio"
        or trigger_id == "split-point-select"
        or trigger_id == "split-point-input"
    ):
        return default_button

    if root_id is None or root_id == "" or vertex_data is None or vertex_data == []:
        return default_button

    datastack_name = get_datastack(url_path)

    client = lib_utils.make_client(
        datastack_name=datastack_name,
        server_address=os.environ.get("GUIDEBOOK_SERVER_ADDRESS"),
        auth_token=None,
    )
    try:
        restriction_point = lib_utils.process_point_string(restriction_point)
    except:
        restriction_point = None

    vertex_df = filter_dataframe(
        root_id=int(root_id),
        vertex_df=rehydrate_dataframe(vertex_data),
        compartment_filter=compartment_filter,
        restriction_direction=point_filter,
        restriction_point=restriction_point,
        only_new_lvl2=only_new_lvl2,
        only_after_timestamp=only_after_timestamp,
        horizon_timestamp=horizon_timestamp,
        client=client,
    )
    if sum(vertex_df[END_POINT_COLUMN]) == 0:
        return url_function(
            f"No Matching {point_name}s",
            button_id=button_id,
            disabled=True,
        )
    else:
        url = states.end_point_link(int(root_id), vertex_df, client)
        return link_maker_button(
            f"{point_name} Link",
            button_id=button_id,
            url=url,
        )


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
        Output("previously-unseen-message", "children"),
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
        num_seen_lvl2_ids = len(seen_lvl2_ids)
        lvl2_message = f"{num_seen_lvl2_ids} previously seen lvl2 ids"
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
                lvl2_message,
            )
        client = lib_utils.make_client(
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
                lvl2_message,
            )

        seen_lvl2_ids = rehydrate_id_list(seen_lvl2_ids)
        vertex_df = process_meshwork_to_dataframe(nrn)
        vertex_df = process_new_points(vertex_df, seen_lvl2_ids)
        disable_compartments = vertex_df["is_axon"].nunique() == 1
        message_text = f"Pre-processed root ID {root_id} with {len(vertex_df)} vertices in {time.time() - t0:.2f} seconds."
        message_color = "green"
        new_seen_lvl2_ids = update_seen_id_list(seen_lvl2_ids, vertex_df)
        return (
            str(root_id),
            stash_dataframe(vertex_df, list_cols=["lvl2_id"]),
            new_seen_lvl2_ids,
            message_text,
            message_color,
            False,
            disable_compartments,
            disable_compartments,
            lvl2_message,
        )

    @app.callback(
        Output("end-point-link-card", "children"),
        State("curr-root-id", "data"),
        State("vertex-df", "data"),
        State("url", "pathname"),
        Input("compartment-radio", "value"),
        Input("split-point-select", "value"),
        Input("split-point-input", "value"),
        Input("new-point-checkbox", "checked"),
        Input("use-time-restriction", "checked"),
        Input("restriction-datetime", "value"),
        Input("timezone-offset", "data"),
        Input("end-point-link-button", "n_clicks"),
        prevent_initial_call=True,
        running=[(Output("end-point-link-button", "loading"), True, False)],
    )
    def generate_end_point_link(
        root_id,
        vertex_data,
        url_path,
        compartment_filter,
        point_filter,
        restriction_point,
        only_new_lvl2,
        use_time_restriction,
        restriction_datetime,
        utc_offset,
        _,
    ):
        end_point_default = (
            link_maker_button(
                "Generate End Point Link",
                button_id="end-point-link-button",
            ),
        )
        return link_process_generic(
            "End Point",
            "end-point-link-button",
            states.end_point_link,
            end_point_default,
            ctx.triggered_id,
            root_id,
            vertex_data,
            url_path,
            compartment_filter,
            point_filter,
            restriction_point,
            only_new_lvl2,
            use_time_restriction,
            convert_time_string_to_utc(restriction_datetime, utc_offset),
        )

    @app.callback(
        Output("restriction-datetime", "disabled"),
        Input("use-time-restriction", "checked"),
    )
    def toggle_time_restrictions(value):
        return not value

    @app.callback(
        Output("datetime-debug-message", "children"),
        State("restriction-datetime", "value"),
        Input("timezone-offset", "data"),
        prevent_initial_call=True,
    )
    def debug_datetime(value, offset):
        return f"Time: {convert_time_string_to_utc(value, offset)}"
