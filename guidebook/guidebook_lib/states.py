from typing import Optional
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


def set_default_ngl_configuration(
    datastack_name: str,
    target_url: str,
    target_site: str = "spelunker",
):
    nglui.statebuilder.site_utils.set_default_config(
        target_site=target_site,
        target_url=target_url,
        datastack_name=datastack_name,
        config_key=datastack_name,
    )


def config_ngl(client, target_url=None, target_site="spelunker"):
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
):
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


def end_point_link(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: str,
    use_skeleton_service: bool = True,
) -> str:
    config_ngl(client)
    sb = make_point_statebuilder(
        layers=["end_points"],
        resolution=client.info.viewer_resolution(),
        use_skeleton_service=use_skeleton_service,
        datastack_name=client.datastack_name,
        split_positions=True,
        root_ids=[root_id],
        client=client,
    )
    return sb.render_state(
        {
            "end_points": vertex_df.query(processing.END_POINT_COLUMN).sort_values(
                by=[
                    processing.IS_AXON_COLUMN,
                    processing.BRANCH_GROUP_COLUMN,
                    processing.DISTANCE_COLUMN,
                ]
            )
        },
        return_as="short",
        config_key=client.datastack_name,
    )


def make_point_statebuilder(
    layers: list,
    resolution: list,
    datastack_name: str,
    use_skeleton_service: bool,
    split_positions: bool,
    client: caveclient.CAVEclient,
    root_ids: list = [],
    layer_colors: dict = {},
    view_kws: dict = {},
):
    img, seg = base_layers(
        client, use_skeleton_service=use_skeleton_service, root_ids=root_ids
    )
    annos = []
    for l in layers:
        annos.append(
            nglui.statebuilder.AnnotationLayerConfig(
                l,
                color=layer_colors.get(l),
                mapping_rules=nglui.statebuilder.PointMapper(
                    processing.VERTEX_POINT,
                    mapping_set=l,
                    split_positions=split_positions,
                ),
                data_resolution=[1, 1, 1],
            ),
        )
    return nglui.statebuilder.StateBuilder(
        [img, seg] + annos,
        view_kws=view_kws,
        config_key=datastack_name,
        resolution=resolution,
        client=client,
    )


def make_path_statebuilder():
    pass


def make_point_link(
    point_dfs: dict,
    point_statebuilder: nglui.statebuilder.StateBuilder,
):
    return point_statebuilder.render_state(
        point_dfs,
        return_as="short",
    )


def make_path_link():
    pass
