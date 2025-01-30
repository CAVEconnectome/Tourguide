from typing import Optional, Union
import nglui
import numpy as np
import pandas as pd
import caveclient

from ..guidebook_app import utils
from . import processing

DEFAULT_SEGMENTATION_VIEW_KWS = {
    "alpha_selected": 0.15,
    "alpha_3d": 0.8,
    "alpha_unselected": 0,
}
DEFAULT_ZOOM = 220_000

LAYER_COLORS = {
    "end_points": "DarkTurquoise",
    "branch_points": "OrangeRed",
}

RESTRICTED_SEGMENTATION_LAYER = "restricted-segmentation"
COVER_PATH_LAYER = "cover-path"


def set_default_ngl_configuration(
    datastack_name: str,
    target_url: str,
    target_site: str = "spelunker",
) -> None:
    nglui.statebuilder.site_utils.set_default_config(
        target_site=target_site,
        target_url=target_url,
        datastack_name=datastack_name,
        config_key=datastack_name,
    )


def config_ngl(client, target_url=None, target_site="spelunker") -> None:
    datastack_name = client.datastack_name
    try:
        nglui.statebuilder.site_utils.get_default_config(datastack_name)
    except KeyError:
        set_default_ngl_configuration(
            datastack_name=datastack_name,
            target_url=target_url,
            target_site=target_site,
        )


def base_layers(
    client: caveclient.CAVEclient,
    use_skeleton_service: bool,
    root_ids: list = [],
) -> tuple:
    img, seg = nglui.statebuilder.from_client(
        client,
        image_name="imagery",
        segmentation_name="seg",
        use_skeleton_service=use_skeleton_service,
        contrast=None,
    )
    seg._view_kws = DEFAULT_SEGMENTATION_VIEW_KWS
    seg.add_selection_map(fixed_ids=root_ids, fixed_id_colors="white")
    return img, seg


def _make_point_link(
    point_link_layers: list,
    root_id: int,
    vertex_df: pd.DataFrame,
    client: caveclient.CAVEclient,
    use_skeleton_service: bool = True,
):
    config_ngl(client)
    sb = make_point_statebuilder(
        layers=point_link_layers,
        resolution=client.info.viewer_resolution(),
        use_skeleton_service=use_skeleton_service,
        split_positions=True,
        root_ids=[root_id],
        view_kws={"zoom_3d": DEFAULT_ZOOM},
        layer_colors=LAYER_COLORS,
        client=client,
    )

    sort_order = [
        processing.IS_AXON_COLUMN,
        processing.BRANCH_GROUP_COLUMN,
        processing.DISTANCE_COLUMN,
    ]

    data_map = {}
    if "end_points" in point_link_layers:
        data_map["end_points"] = vertex_df.query(
            processing.END_POINT_COLUMN
        ).sort_values(by=sort_order)
    if "branch_points" in point_link_layers:
        data_map["branch_points"] = vertex_df.query(
            processing.BRANCH_POINT_COLUMN
        ).sort_values(by=sort_order)
    return sb.render_state(
        data_map,
        return_as="short",
        config_key=client.datastack_name,
    )


def end_point_link(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: str,
    use_skeleton_service: bool = True,
) -> str:
    return _make_point_link(
        ["end_points"],
        root_id,
        vertex_df,
        client,
        use_skeleton_service,
    )


def branch_point_link(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: str,
    use_skeleton_service: bool = True,
) -> str:
    return _make_point_link(
        ["branch_points"],
        root_id,
        vertex_df,
        client,
        use_skeleton_service,
    )


def branch_end_point_link(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: str,
    use_skeleton_service: bool = True,
) -> str:
    return _make_point_link(
        ["end_points", "branch_points"],
        root_id,
        vertex_df,
        client,
        use_skeleton_service,
    )


def _make_point_annotation_layer(
    layer_name: str,
    color: Union[tuple, str],
    split_positions: bool,
):
    return (
        nglui.statebuilder.AnnotationLayerConfig(
            layer_name,
            color=color,
            mapping_rules=nglui.statebuilder.PointMapper(
                processing.VERTEX_POINT,
                mapping_set=layer_name,
                split_positions=split_positions,
            ),
            data_resolution=[1, 1, 1],
        ),
    )


def make_point_statebuilder(
    layers: list,
    resolution: list,
    use_skeleton_service: bool,
    split_positions: bool,
    client: caveclient.CAVEclient,
    root_ids: list = [],
    layer_colors: dict = {},
    view_kws: dict = {},
) -> nglui.statebuilder.StateBuilder:
    img, seg = base_layers(
        client, use_skeleton_service=use_skeleton_service, root_ids=root_ids
    )
    annos = []
    for l in layers:
        annos.append(
            _make_point_annotation_layer(
                layer_name=l,
                color=layer_colors.get(l),
                split_positions=split_positions,
            )
        )
    return nglui.statebuilder.StateBuilder(
        [img, seg] + annos,
        view_kws=view_kws,
        config_key=client.datastack_name,
        resolution=resolution,
        client=client,
    )


def make_point_link(
    point_dfs: dict,
    point_statebuilder: nglui.statebuilder.StateBuilder,
) -> str:
    return point_statebuilder.render_state(
        point_dfs,
        return_as="short",
    )


def _path_annotation_layer(
    layer_name: str,
    color: str,
    split_positions: bool,
    pointA="pointA",
    pointB="pointB",
):
    return nglui.statebuilder.AnnotationLayerConfig(
        layer_name,
        color=color,
        mapping_rules=nglui.statebuilder.LineMapper(
            point_column_a=pointA,
            point_column_b=pointB,
            mapping_set=layer_name,
            split_positions=split_positions,
        ),
        data_resolution=[1, 1, 1],
    )


def make_path_statebuilder(
    color: Union[tuple, str],
    use_skeleton_service: bool,
    split_positions: bool,
    client: caveclient.CAVEclient,
    root_ids: list = [],
    view_kws: dict = {},
    add_restricted_segmentation_layer: bool = False,
    restricted_color: Optional[Union[tuple, str]] = None,
):
    if add_restricted_segmentation_layer:
        img, seg = base_layers(client, use_skeleton_service=use_skeleton_service)
    else:
        img, seg = base_layers(
            client, use_skeleton_service=use_skeleton_service, root_ids=root_ids
        )
    path_anno = _path_annotation_layer(
        layer_name=COVER_PATH_LAYER,
        color=color,
        split_positions=split_positions,
    )
    layers = [img, seg, path_anno]
    if restricted_color is None:
        restricted_color = color
    if add_restricted_segmentation_layer:
        layers.append(
            make_restricted_segmentation_layer(
                layer_name=RESTRICTED_SEGMENTATION_LAYER,
                client=client,
                color=restricted_color,
            )
        )
    return nglui.statebuilder.StateBuilder(
        layers,
        view_kws=view_kws,
        config_key=client.datastack_name,
        resolution=client.info.viewer_resolution(),
        client=client,
    )


def make_restricted_segmentation_layer(
    layer_name: str,
    client: caveclient.CAVEclient,
    color: Optional[Union[tuple, str]] = None,
):
    if color is None:
        color = "white"
    return nglui.statebuilder.SegmentationLayerConfig(
        client.info.segmentation_source(),
        name=layer_name,
        selected_ids_column="selected_id",
        mapping_set=RESTRICTED_SEGMENTATION_LAYER,
        color_column="color",
        alpha_selected=0,
        alpha_3d=0.3,
        selectable=False,
    )


def make_path_link(
    path_df: pd.DataFrame,
    path_statebuilder: nglui.statebuilder.StateBuilder,
    client: caveclient.CAVEclient,
) -> str:
    return path_statebuilder.render_state(
        path_df, return_as="short", config_key=client.datastack_name
    )


def package_path_data(
    path_df: Optional[pd.DataFrame] = None,
    lvl2_ids: Optional[list] = None,
    mesh_only: bool = False,
    mesh_color: Optional[Union[tuple, str]] = None,
    client: Optional[caveclient.CAVEclient] = None,
):
    if mesh_only:
        data_package = {}
    else:
        data_package = {COVER_PATH_LAYER: path_df}
    if lvl2_ids is not None and client is not None:
        min_cover_ids = client.chunkedgraph.get_minimal_covering_nodes(lvl2_ids)
        if mesh_color is None:
            mesh_color = "white"
        data_package[RESTRICTED_SEGMENTATION_LAYER] = pd.DataFrame(
            {
                "selected_id": min_cover_ids,
                "color": mesh_color,
            }
        )
    return data_package
