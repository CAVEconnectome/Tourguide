import logging
from typing import Optional
import flask
from dash import html, dcc, Input, Output, State, ctx, no_update
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
    process_paths,
    VERTEX_COLUMNS,
    END_POINT_COLUMN,
    BRANCH_GROUP_COLUMN,
    LVL2_ID_COLUMN,
)
from ...guidebook_lib import states, lib_utils
from pcg_skel import get_meshwork_from_client
import pandas as pd
import time
import os
from urllib.parse import parse_qs, urlparse, urlencode
from datetime import datetime, timezone


import logging

if os.environ.get("GUIDEBOOK_VERBOSE_LOG", "false") == "true":
    logging.getLogger().setLevel(logging.INFO)

VERTEX_LIST_COLS = ["lvl2_id"]

RESET_LINK_TRIGGERS = [
    "use-time-restriction",
    "restriction-datetime",
    "new-point-checkbox",
    "split-point-input",
    "split-point-select",
    "compartment-radio",
    "show-mesh-subset",
    "hide-path",
    "ignore-short-paths",
    "smooth-paths-input",
    "smooth-paths-checkbox",
    "topo-restriction-select",
    "topo-restriction-input",
    "annotation-tag-list",
]

SHORT_PATH_LENGTH = 5_000


def get_datastack(pathname):
    if pathname is not None:
        return pathname.split("/")[-1]
    else:
        return None


def _url_query_dict(search_qry):
    if search_qry is None or search_qry == "":
        return {}
    else:
        return parse_qs(urlparse(search_qry).query)


def root_id_from_url_query(search_qry):
    root_id = _url_query_dict(search_qry).get("root_id", [None])[0]
    try:
        return root_id
    except:
        return None


def url_query_from_root_id(root_id):
    return "?" + urlencode(query={"root_id": str(root_id)})


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
    topo_restriction,
    topo_restriction_value,
    only_new_lvl2,
    only_after_timestamp,
    horizon_timestamp,
    is_path=False,
    ignore_short_paths=None,
    show_mesh_subset=None,
    hide_path=None,
    smooth_paths=None,
    smooth_paths_distance=None,
    tags=None,
):
    # Not having good data should also reset the links
    if root_id is None or root_id == "" or vertex_data is None or vertex_data == []:
        return (
            link_maker_button(
                f"Generate {point_name} Link",
                button_id=button_id,
                disabled=True,
            ),
        )

    # Adjusting filters should reset the links
    if trigger_id in RESET_LINK_TRIGGERS:
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
    logging.info(f"\tRestriction Point: {restriction_point}")

    if topo_restriction == "no-split":
        max_branch_to_root = None
        max_distance_to_root = None
    elif topo_restriction == "branch-topo":
        max_branch_to_root = int(topo_restriction_value)
        max_distance_to_root = None
    elif topo_restriction == "distance-topo":
        max_branch_to_root = None
        max_distance_to_root = int(topo_restriction_value) * 1_000

    if not is_path:
        logging.info(f"Working on point links")
        vertex_df = filter_dataframe(
            root_id=int(root_id),
            vertex_df=rehydrate_dataframe(vertex_data, list_columns=[LVL2_ID_COLUMN]),
            compartment_filter=compartment_filter,
            restriction_direction=point_filter,
            restriction_point=restriction_point,
            only_new_lvl2=only_new_lvl2,
            only_after_timestamp=only_after_timestamp,
            horizon_timestamp=horizon_timestamp,
            max_branch_to_root=max_branch_to_root,
            max_distance_to_root=max_distance_to_root,
            client=client,
        )
        logging.info(f"vertex_df: {len(vertex_df)} points")

        if sum(vertex_df[END_POINT_COLUMN]) == 0:
            return link_maker_button(
                f"No Matching {point_name}s",
                button_id=button_id,
                disabled=True,
            )
        else:
            url = url_function(
                int(root_id),
                vertex_df,
                client,
                tags=tags,
            )
            logging.info(f"Generating button with url: {url}")
            return link_maker_button(
                f"{point_name} Link",
                button_id=button_id,
                url=url,
            )
    else:
        if ignore_short_paths:
            min_path_length = SHORT_PATH_LENGTH
        else:
            min_path_length = None
        logging.info(f"\tSmooth Paths: {smooth_paths}")
        if smooth_paths:
            step_size = smooth_paths_distance
        else:
            step_size = None
        logging.info(f"\tStep Size: {step_size}")
        vertex_df = rehydrate_dataframe(vertex_data, list_columns=[LVL2_ID_COLUMN])
        path_df, lvl2_ids = process_paths(
            root_id=int(root_id),
            vertex_df=vertex_df,
            client=client,
            compartment_filter=compartment_filter,
            restriction_direction=point_filter,
            restriction_point=restriction_point,
            max_branch_to_root=max_branch_to_root,
            max_distance_to_root=max_distance_to_root,
            only_new_lvl2=only_new_lvl2,
            only_after_timestamp=only_after_timestamp,
            horizon_timestamp=horizon_timestamp,
            min_path_length=min_path_length,
            return_l2_ids=show_mesh_subset,
            step_size=step_size,
        )
        if show_mesh_subset:
            logging.info(f"\tpath df: {len(path_df)}. lvl2_ids: {len(lvl2_ids)}")
        else:
            logging.info(f"\tpath df: {len(path_df)}, lvl2_ids: None")
        sb_data = states.package_path_data(
            path_df,
            lvl2_ids,
            mesh_only=hide_path,
            client=client,
        )

        logging.info(f"\tMade sb_data: {{k: len(v) for k, v in sb_data.items()}}")
        if len(vertex_df) == 0:
            return link_maker_button(
                f"No Matching {point_name}s",
                button_id=button_id,
                disabled=True,
            )
        else:
            logging.info(f"Making statebuilder for paths")
            sb = states.make_path_statebuilder(
                color="white",
                use_skeleton_service=True,
                split_positions=True,
                client=client,
                root_ids=[int(root_id)],
                add_restricted_segmentation_layer=show_mesh_subset,
                restricted_color="white",
                tags=tags,
            )
            url = url_function(sb_data, sb, client)
            logging.info(f"Generating button with url: {url}")
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

    @app.callback(
        Output("guidebook-root-id", "value", allow_duplicate=True),
        Input("url", "search"),
        prevent_initial_call="initial_duplicate",
    )
    def set_root_id(search):
        return root_id_from_url_query(search)

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
        Output("seen-lvl2-ids", "data", allow_duplicate=True),
        Output("message-text", "children"),
        Output("message-text", "color"),
        Output("end-point-link-button", "disabled"),
        Output("branch-point-link-button", "disabled"),
        Output("branch-end-point-link-button", "disabled", allow_duplicate=True),
        Output("path-link-button", "disabled"),
        Output("radio-axon", "disabled"),
        Output("radio-dendrite", "disabled"),
        Output("url", "search"),
        Output("guidebook-root-id", "value", allow_duplicate=True),
        [
            State("guidebook-root-id", "value"),
            State("url", "pathname"),
            Input("submit-button", "n_clicks"),
            Input("update-id-button", "n_clicks"),
            State("seen-lvl2-ids", "data"),
        ],
        prevent_initial_call=True,
        running=[
            (Output("submit-button", "loading"), True, False),
            (Output("update-id-button", "loading"), True, False),
        ],
    )
    def process_root_id(root_id, url, _, __, seen_lvl2_ids):
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
                True,
                True,
                True,
                None,
                no_update,
            )
        client = lib_utils.make_client(
            get_datastack(url),
            server_address=os.environ.get("GUIDEBOOK_SERVER_ADDRESS"),
            auth_token=None,
        )
        if ctx.triggered_id == "update-id-button":
            new_root_id = client.chunkedgraph.suggest_latest_roots(int(root_id))
            if new_root_id == int(root_id):
                root_id_updated = False
            else:
                root_id_updated = True
                old_id = root_id
                root_id = new_root_id
        else:
            root_id_updated = False

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
                True,
                True,
                True,
                url_query_from_root_id(root_id),
                no_update,
            )

        seen_lvl2_ids = rehydrate_id_list(seen_lvl2_ids)
        vertex_df = process_meshwork_to_dataframe(nrn)
        vertex_df = process_new_points(vertex_df, seen_lvl2_ids)
        disable_compartments = vertex_df["is_axon"].nunique() == 1
        if root_id_updated:
            message_text = f"Pre-processed root ID {root_id} (updated from {old_id}) with {len(vertex_df)} vertices in {time.time() - t0:.2f} seconds."
            message_color = "violet"
        else:
            message_text = f"Pre-processed root ID {root_id} with {len(vertex_df)} vertices in {time.time() - t0:.2f} seconds."
            message_color = "green"
        new_seen_lvl2_ids = update_seen_id_list(seen_lvl2_ids, vertex_df)
        return (
            str(root_id),
            stash_dataframe(vertex_df, list_cols=[LVL2_ID_COLUMN]),
            new_seen_lvl2_ids,
            message_text,
            message_color,
            False,
            False,
            False,
            False,
            disable_compartments,
            disable_compartments,
            url_query_from_root_id(root_id),
            root_id,
        )

    @app.callback(
        Output("end-point-link-card", "children"),
        State("curr-root-id", "data"),
        State("vertex-df", "data"),
        State("url", "pathname"),
        Input("compartment-radio", "value"),
        Input("split-point-select", "value"),
        Input("split-point-input", "value"),
        Input("topo-restriction-select", "value"),
        Input("topo-restriction-input", "value"),
        Input("new-point-checkbox", "checked"),
        Input("use-time-restriction", "checked"),
        Input("restriction-datetime", "value"),
        Input("timezone-offset", "data"),
        Input("annotation-tag-list", "value"),
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
        topo_restriction,
        topo_restriction_value,
        only_new_lvl2,
        use_time_restriction,
        restriction_datetime,
        utc_offset,
        tags,
        _,
    ):
        point_name = "End Point"
        button_id = "end-point-link-button"
        default_button = (
            link_maker_button(
                f"Generate {point_name} Link",
                button_id=button_id,
            ),
        )

        return link_process_generic(
            point_name,
            button_id,
            states.end_point_link,
            default_button,
            ctx.triggered_id,
            root_id,
            vertex_data,
            url_path,
            compartment_filter,
            point_filter,
            restriction_point,
            topo_restriction,
            topo_restriction_value,
            only_new_lvl2,
            use_time_restriction,
            convert_time_string_to_utc(restriction_datetime, utc_offset),
            tags=tags,
        )

    @app.callback(
        Output("branch-point-link-card", "children"),
        State("curr-root-id", "data"),
        State("vertex-df", "data"),
        State("url", "pathname"),
        Input("compartment-radio", "value"),
        Input("split-point-select", "value"),
        Input("split-point-input", "value"),
        Input("topo-restriction-select", "value"),
        Input("topo-restriction-input", "value"),
        Input("new-point-checkbox", "checked"),
        Input("use-time-restriction", "checked"),
        Input("restriction-datetime", "value"),
        Input("timezone-offset", "data"),
        Input("annotation-tag-list", "value"),
        Input("branch-point-link-button", "n_clicks"),
        prevent_initial_call=True,
        running=[(Output("branch-point-link-button", "loading"), True, False)],
    )
    def generate_branch_point_link(
        root_id,
        vertex_data,
        url_path,
        compartment_filter,
        point_filter,
        restriction_point,
        topo_restriction,
        topo_restriction_value,
        only_new_lvl2,
        use_time_restriction,
        restriction_datetime,
        utc_offset,
        tags,
        _,
    ):
        point_name = "Branch Point"
        button_id = "branch-point-link-button"
        default_button = (
            link_maker_button(
                f"Generate {point_name} Link",
                button_id=button_id,
            ),
        )

        return link_process_generic(
            point_name,
            button_id,
            states.branch_point_link,
            default_button,
            ctx.triggered_id,
            root_id,
            vertex_data,
            url_path,
            compartment_filter,
            point_filter,
            restriction_point,
            topo_restriction,
            topo_restriction_value,
            only_new_lvl2,
            use_time_restriction,
            convert_time_string_to_utc(restriction_datetime, utc_offset),
            tags=tags,
        )

    @app.callback(
        Output("branch-end-point-link-card", "children"),
        State("curr-root-id", "data"),
        State("vertex-df", "data"),
        State("url", "pathname"),
        Input("compartment-radio", "value"),
        Input("split-point-select", "value"),
        Input("split-point-input", "value"),
        Input("topo-restriction-select", "value"),
        Input("topo-restriction-input", "value"),
        Input("new-point-checkbox", "checked"),
        Input("use-time-restriction", "checked"),
        Input("restriction-datetime", "value"),
        Input("timezone-offset", "data"),
        Input("annotation-tag-list", "value"),
        Input("branch-end-point-link-button", "n_clicks"),
        prevent_initial_call=True,
        running=[(Output("branch-end-point-link-button", "loading"), True, False)],
    )
    def generate_branch_end_point_link(
        root_id,
        vertex_data,
        url_path,
        compartment_filter,
        point_filter,
        restriction_point,
        topo_restriction,
        topo_restriction_value,
        only_new_lvl2,
        use_time_restriction,
        restriction_datetime,
        utc_offset,
        tags,
        _,
    ):
        point_name = "Branch and End Point"
        button_id = "branch-end-point-link-button"
        default_button = (
            link_maker_button(
                f"Generate {point_name} Link",
                button_id=button_id,
            ),
        )
        return link_process_generic(
            point_name,
            button_id,
            states.branch_end_point_link,
            default_button,
            ctx.triggered_id,
            root_id,
            vertex_data,
            url_path,
            compartment_filter,
            point_filter,
            restriction_point,
            topo_restriction,
            topo_restriction_value,
            only_new_lvl2,
            use_time_restriction,
            convert_time_string_to_utc(restriction_datetime, utc_offset),
            tags=tags,
        )

    @app.callback(
        Output("restriction-datetime", "disabled"),
        Input("use-time-restriction", "checked"),
    )
    def toggle_time_restrictions(value):
        return not value

    @app.callback(
        Output("split-point-input", "disabled"),
        Output("split-point-input", "value"),
        Output("split-point-input", "error"),
        Input("split-point-select", "value"),
        Input("split-point-input", "value"),
    )
    def toggle_split_point_input(split_value, input_value):
        error_value = None
        if input_value is not None or input_value != "":
            try:
                pt = [float(x) for x in input_value.split(",")]
                if len(pt) != 3:
                    error_value = "Use 3 comma-separated numbers"
            except:
                error_value = "Use 3 comma-separated numbers"

        if split_value == "no-split":
            return True, "", None
        return False, input_value, error_value

    @app.callback(
        Output("topo-restriction-input", "disabled"),
        Output("topo-restriction-input", "value"),
        Input("topo-restriction-select", "value"),
        Input("topo-restriction-input", "value"),
    )
    def toggle_topo_restriction_input(select_value, input_value):
        if select_value == "no-split":
            return True, ""
        return False, input_value

    @app.callback(
        Output("clear-history-modal", "opened"),
        Input("clear-history-modal-toggle", "n_clicks"),
        Input("clear-history-confirm", "n_clicks"),
        Input("clear-history-cancel", "n_clicks"),
        State("clear-history-modal", "opened"),
        prevent_initial_call=True,
    )
    def toggle_clear_history_modal(n_cl1, n_cl2, n_cl3, opened):
        return not opened

    @app.callback(
        Output("seen-lvl2-ids", "data", allow_duplicate=True),
        Input("clear-history-confirm", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_seen_lvl2_ids(_):
        return []

    @app.callback(
        Output("previously-unseen-message", "children"),
        Input("seen-lvl2-ids", "data"),
    )
    def previously_seen_lvl2_ids(seen_lvl2_ids):
        return f"{len(seen_lvl2_ids)} previously seen vertex ids"

    @app.callback(
        Output("restriction-datetime", "error"),
        Input("restriction-datetime", "value"),
        State("timezone-offset", "data"),
        prevent_initial_call=True,
    )
    def validate_datetime(ts, utc_offset):
        if (
            convert_time_string_to_utc(ts, utc_offset)
            > datetime.now(timezone.utc).timestamp()
        ):
            return "Time selected is in the future"

    @app.callback(
        Output("hide-path", "checked"),
        Output("hide-path", "disabled"),
        Input("show-mesh-subset", "checked"),
    )
    def toggle_hide_path(value):
        if value:
            return False, False
        else:
            return False, True

    @app.callback(
        Output("smooth-paths-input", "disabled"),
        Input("smooth-paths-checkbox", "checked"),
    )
    def toggle_smooth_path(value):
        return not value

    @app.callback(
        Output("path-link-card", "children"),
        State("curr-root-id", "data"),
        State("vertex-df", "data"),
        State("url", "pathname"),
        Input("compartment-radio", "value"),
        Input("split-point-select", "value"),
        Input("split-point-input", "value"),
        Input("topo-restriction-select", "value"),
        Input("topo-restriction-input", "value"),
        Input("new-point-checkbox", "checked"),
        Input("use-time-restriction", "checked"),
        Input("restriction-datetime", "value"),
        Input("timezone-offset", "data"),
        Input("ignore-short-paths", "checked"),
        Input("show-mesh-subset", "checked"),
        Input("hide-path", "checked"),
        Input("smooth-paths-checkbox", "checked"),
        Input("smooth-paths-input", "value"),
        Input("annotation-tag-list", "value"),
        Input("path-link-button", "n_clicks"),
        prevent_initial_call=True,
        running=[(Output("path-link-button", "loading"), True, False)],
    )
    def generate_path_link(
        root_id,
        vertex_data,
        url_path,
        compartment_filter,
        point_filter,
        restriction_point,
        topo_restriction,
        topo_restriction_value,
        only_new_lvl2,
        use_time_restriction,
        restriction_datetime,
        utc_offset,
        ignore_short_paths,
        show_mesh_subset,
        hide_path,
        smooth_paths,
        smooth_paths_distance,
        tags,
        _,
    ):
        point_name = "Path"
        button_id = "path-link-button"
        default_button = (
            link_maker_button(
                f"Generate {point_name} Link",
                button_id=button_id,
            ),
        )
        logging.info(f"Generating path link for root ID {root_id}")
        logging.info(f"Triggered by: {ctx.triggered_id}")
        return link_process_generic(
            point_name=point_name,
            button_id=button_id,
            url_function=states.make_path_link,
            default_button=default_button,
            trigger_id=ctx.triggered_id,
            root_id=root_id,
            vertex_data=vertex_data,
            url_path=url_path,
            compartment_filter=compartment_filter,
            point_filter=point_filter,
            restriction_point=restriction_point,
            topo_restriction=topo_restriction,
            topo_restriction_value=topo_restriction_value,
            only_new_lvl2=only_new_lvl2,
            only_after_timestamp=use_time_restriction,
            horizon_timestamp=convert_time_string_to_utc(
                restriction_datetime, utc_offset
            ),
            is_path=True,
            ignore_short_paths=ignore_short_paths,
            show_mesh_subset=show_mesh_subset,
            hide_path=hide_path,
            smooth_paths=smooth_paths,
            smooth_paths_distance=smooth_paths_distance,
            tags=tags,
        )
