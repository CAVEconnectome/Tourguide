from typing import Optional
import nglui
import numpy as np
import pandas as pd
import caveclient

from ..guidebook_app import utils
from . import processing

PT_COLUMN_NAME = "pt_position"


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


def base_layers(
    client: caveclient.CAVEclient,
    use_skeleton_service: bool,
):
    return nglui.statebuilder.from_client(
        client,
        image_name="imagery",
        segmentation_name="seg",
        use_skeleton_service=use_skeleton_service,
        contrast=None,
    )


def make_point_statebuilder(
    layers: list,
    layer_colors: dict,
    resolution: list,
    datastack_name: str,
    use_skeleton_service: bool,
    client: caveclient.CAVEclient,
    view_kws: Optional[dict] = None,
):
    img, seg = base_layers(client, use_skeleton_service=use_skeleton_service)
    annos = []
    for l in layers:
        annos.append(
            nglui.statebuilder.AnnotationLayerConfig(
                l,
                color=layer_colors.get(l),
                mapping_rules=nglui.statebuilder.PointMapper(
                    PT_COLUMN_NAME, mapping_set=l
                ),
            )
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
