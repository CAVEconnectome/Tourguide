from typing import Optional, Union
from nglui.statebuilder import *
import numpy as np
import pandas as pd
from caveclient.frameworkclient import CAVEclientFull as CAVEclient
import os

from ..tourguide_app import utils
from . import processing

DEFAULT_SEGMENTATION_VIEW_KWS = {
    "selected_alpha": 0.15,
    "alpha_3d": 0.8,
    "not_selected_alpha": 0,
    "mesh_silhouette": 0.05,
}
DEFAULT_ZOOM = 220_000

LAYER_COLORS = {
    "end_points": "DarkTurquoise",
    "branch_points": "OrangeRed",
}

RESTRICTED_SEGMENTATION_LAYER = "restricted-segmentation"
COVER_PATH_LAYER = "cover-path"
DEFAULT_NEUROGLANCER_URL = os.environ.get(
    "TOURGUIDE_NEUROGLANCER_URL", "https://spelunker.cave-explorer.org"
)

POINT_SORT_ORDER = [
    processing.IS_AXON_COLUMN,
    processing.BRANCH_GROUP_COLUMN,
    processing.DISTANCE_COLUMN,
]


def set_default_ngl_configuration(
    datastack_name: str,
    target_url: Optional[str] = None,
) -> None:
    add_neuroglancer_site(
        site_name=datastack_name,
        site_url=target_url or DEFAULT_NEUROGLANCER_URL,
    )


def config_ngl(client: CAVEclient, target_url: Optional[str] = None) -> None:
    datastack_name = client.datastack_name
    if client.datastack_name not in get_neuroglancer_sites():
        set_default_ngl_configuration(
            datastack_name=datastack_name,
            target_url=target_url,
        )


def base_layers(
    client: CAVEclient,
    use_skeleton_service: bool,
    root_ids: list = [],
    seg_colors: Optional[Union[list, dict]] = "white",
) -> ViewerState:
    seg_source = [client.info.segmentation_source()]
    if use_skeleton_service:
        sk_source = client.info.get_datastack_info().get("skeleton_source")
        if sk_source:
            seg_source.append(sk_source)
    if isinstance(seg_colors, str):
        seg_colors = {x: seg_colors for x in root_ids}
    return (
        ViewerState(dimensions=client.info.viewer_resolution())
        .add_image_layer(
            source=client.info.image_source(),
        )
        .add_segmentation_layer(
            source=seg_source,
            segments=root_ids,
            segment_colors=seg_colors,
            **DEFAULT_SEGMENTATION_VIEW_KWS,
        )
    )


def _add_end_points(
    viewer_state: ViewerState,
    vertex_df: pd.DataFrame,
    tags: list[str],
) -> ViewerState:
    return viewer_state.add_points(
        data=vertex_df.query(processing.END_POINT_COLUMN).sort_values(
            by=POINT_SORT_ORDER
        ),
        name="end_points",
        point_column=processing.VERTEX_POINT,
        tags=tags,
        data_resolution=[1, 1, 1],
        color=LAYER_COLORS.get("end_points", "DarkTurquoise"),
        swap_visible_segments_on_move=False,
    )


def _add_branch_points(
    viewer_state: ViewerState,
    vertex_df: pd.DataFrame,
    tags: list[str],
) -> ViewerState:
    viewer_state.add_points(
        data=vertex_df.query(processing.BRANCH_POINT_COLUMN).sort_values(
            by=POINT_SORT_ORDER
        ),
        name="branch_points",
        point_column=processing.VERTEX_POINT,
        tags=tags,
        data_resolution=[1, 1, 1],
        swap_visible_segments_on_move=False,
    )
    viewer_state.layers[-1].color = LAYER_COLORS.get("branch_points", "OrangeRed")
    return viewer_state


def end_point_link(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: CAVEclient,
    use_skeleton_service: bool = True,
    tags: Optional[list] = None,
) -> str:
    config_ngl(client)

    viewer_state = base_layers(
        client=client,
        use_skeleton_service=use_skeleton_service,
        root_ids=[root_id],
    )
    return _add_end_points(
        viewer_state,
        vertex_df=vertex_df,
        tags=tags or [],
    ).to_link_shortener(client=client, target_site=client.datastack_name)


def branch_point_link(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: str,
    use_skeleton_service: bool = True,
    tags: Optional[list] = None,
) -> str:
    config_ngl(client)

    viewer_state = base_layers(
        client=client,
        use_skeleton_service=use_skeleton_service,
        root_ids=[root_id],
    )
    return _add_branch_points(
        viewer_state,
        vertex_df=vertex_df,
        tags=tags or [],
    ).to_link_shortener(client=client, target_site=client.datastack_name)


def branch_end_point_link(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: str,
    use_skeleton_service: bool = True,
    tags: Optional[list] = None,
) -> str:
    config_ngl(client)

    viewer_state = base_layers(
        client=client,
        use_skeleton_service=use_skeleton_service,
        root_ids=[root_id],
    )
    viewer_state = _add_end_points(
        viewer_state,
        vertex_df=vertex_df,
        tags=tags or [],
    )
    return _add_branch_points(
        viewer_state,
        vertex_df=vertex_df,
        tags=tags or [],
    ).to_link_shortener(client=client, target_site=client.datastack_name)


def make_path_link(
    client: CAVEclient,
    root_id: int,
    path_df: Optional[pd.DataFrame] = None,
    use_skeleton_service: bool = True,
    lvl2_ids: Optional[list] = None,
    mesh_only: bool = False,
    mesh_color: Optional[Union[tuple, str]] = None,
    color: Optional[Union[str, tuple]] = None,
    add_restricted_segmentation_layer: bool = False,
    restricted_color: Optional[Union[tuple, str]] = None,
    tags: Optional[list[str]] = None,
) -> str:
    config_ngl(client)

    if not add_restricted_segmentation_layer:
        root_ids = [root_id]
    else:
        root_ids = []
    viewer_state = base_layers(
        client=client,
        use_skeleton_service=use_skeleton_service,
        root_ids=root_ids,
    )
    if not mesh_only and path_df is not None:
        viewer_state.add_lines(
            data=path_df,
            name=COVER_PATH_LAYER,
            point_a_column="pointA",
            point_b_column="pointB",
            data_resolution=[1, 1, 1],
            tags=tags,
            swap_visible_segments_on_move=False,
        )
        viewer_state.layers[-1].color = color

    if (
        add_restricted_segmentation_layer
        and lvl2_ids is not None
        and client is not None
    ):
        more_root_ids = client.chunkedgraph.get_minimal_covering_nodes(lvl2_ids)
        if mesh_color is None:
            mesh_color = "white"
        viewer_state.add_segmentation_layer(
            source=client.info.segmentation_source(),
            segments=more_root_ids,
            segment_colors={x: restricted_color or "white" for x in more_root_ids},
            name=RESTRICTED_SEGMENTATION_LAYER,
            selected_alpha=0,
            alpha_3d=0.3,
            pick=False,
        )
    return viewer_state.to_link_shortener(
        client=client,
        target_site=client.datastack_name,
    )
