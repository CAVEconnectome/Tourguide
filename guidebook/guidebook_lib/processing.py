import numpy as np
from meshparty import meshwork, skeleton
from typing import Literal, Optional
import pandas as pd
from scipy import sparse
import caveclient
from pcg_skel import chunk_tools
from datetime import datetime

import logging
import os

if os.environ.get("GUIDEBOOK_VERBOSE_LOG", "false") == "true":
    logging.getLogger().setLevel(logging.INFO)


VERTEX_POINT = "pt"
VERTEX_COLUMNS = [f"{VERTEX_POINT}_{suf}" for suf in ["x", "y", "z"]]
PATH_VERTEX_A_POINT = "pointA"
PATH_VERTEX_B_POINT = "pointB"
PATH_VERTEX_COLUMNS = [
    f"{pre}_{suf}"
    for pre in [PATH_VERTEX_A_POINT, PATH_VERTEX_B_POINT]
    for suf in ["x", "y", "z"]
]
BRANCH_GROUP_COLUMN = "branch_group"
DISTANCE_COLUMN = "distance_to_root"
IS_AXON_COLUMN = "is_axon"
PARENT_COLUMN = "parent"
LVL2_ID_COLUMN = "lvl2_id"
END_POINT_COLUMN = "is_end"
BRANCH_POINT_COLUMN = "is_branch"
ROOT_COLUMN = "is_root"
NEW_POINT_COLUMN = "is_new_point"
NEW_TIMESTAMP_COLUMN = "not_in_previous_match"
NUM_BRANCH_TO_ROOT_COLUMN = "num_bp_to_root"

RESTRICT_OPTIONS = ["upstream-of", "downstream-of"]


def process_meshwork_to_dataframe(
    nrn: meshwork.Meshwork,
) -> pd.DataFrame:
    """Process a meshwork object into a rich vertex dataframe"""
    verts = nrn.skeleton.vertices.astype(int)
    is_axon = nrn.anno.is_axon.mesh_index.to_skel_mask

    l2df = nrn.anno.lvl2_ids.df
    l2df["skind"] = nrn.skeleton.mesh_to_skel_map

    vert_df = pd.DataFrame(
        {
            VERTEX_COLUMNS[0]: verts[:, 0],
            VERTEX_COLUMNS[1]: verts[:, 1],
            VERTEX_COLUMNS[2]: verts[:, 2],
            IS_AXON_COLUMN: is_axon,
            PARENT_COLUMN: nrn.skeleton.parent_nodes(nrn.skeleton_indices),
            DISTANCE_COLUMN: nrn.skeleton.distance_to_root,
            BRANCH_GROUP_COLUMN: branch_group_label(nrn),
            NUM_BRANCH_TO_ROOT_COLUMN: num_branch_points(nrn),
            LVL2_ID_COLUMN: l2df.groupby("skind")[LVL2_ID_COLUMN].agg(list),
        }
    )
    vert_df[END_POINT_COLUMN] = False
    vert_df.loc[nrn.skeleton.end_points, END_POINT_COLUMN] = True

    vert_df[BRANCH_POINT_COLUMN] = False
    vert_df.loc[nrn.skeleton.branch_points, BRANCH_POINT_COLUMN] = True

    vert_df[ROOT_COLUMN] = False
    vert_df.loc[int(nrn.skeleton.root), ROOT_COLUMN] = True
    logging.info(
        f"Processed meshwork to dataframe with root at {int(nrn.skeleton.root)}"
    )
    return vert_df


def num_branch_points(nrn):
    n_bp = np.zeros(len(nrn.skeleton.vertices), dtype=int)
    bp = nrn.skeleton.branch_points
    for bp, ds_list in zip(bp, nrn.skeleton.downstream_nodes(bp)):
        _bp[ds_list] = n_bp[ds_list] + 1
    return n_bp


def branch_group_label(nrn, cp_max_thresh=200_000):
    "Label vertices by branch groups around long cover paths."
    sk = nrn.skeleton
    cps = sk.cover_paths
    cp_lens = [sk.path_length(cp) for cp in cps]
    cp_ends = np.array([cp[-1] for cp in cps])

    # Internal use only
    cp_df = pd.DataFrame({"cps": cps, "pathlen": cp_lens, "ends": cp_ends})
    cp_df["root_parent"] = sk.parent_nodes(cp_df["ends"])

    clip = cp_df["pathlen"] > cp_max_thresh
    cp_df[clip].query("root_parent != -1")
    clip_points = cp_df[clip].query("root_parent != -1")["ends"]
    extra_clip_points = sk.child_nodes(sk.root)
    all_clip_pts = np.unique(np.concatenate([clip_points, extra_clip_points]))

    _, lbls = sparse.csgraph.connected_components(sk.cut_graph(all_clip_pts))
    min_dist_label = [np.min(sk.distance_to_root[lbls == l]) for l in np.unique(lbls)]
    labels_ordered = np.unique(lbls)[np.argsort(min_dist_label)]
    new_lbls = np.argsort(labels_ordered)[lbls]
    return new_lbls


def _skeleton_from_vertex_df(vert_df: pd.DataFrame) -> skeleton.Skeleton:
    return skeleton.Skeleton(
        vertices=vert_df[VERTEX_COLUMNS].values,
        edges=vert_df.query(f"{PARENT_COLUMN}!=-1")[PARENT_COLUMN].reset_index().values,
        root=int(vert_df.query(ROOT_COLUMN).index[0]),
    )


def add_downstream_column(
    vert_df: pd.DataFrame,
    base_lvl2_id: int,
    downstream_column: str = "is_downstream",
    inclusive: bool = True,
    sk=None,
) -> pd.DataFrame:
    """Add a boolean column to a vertex dataframe indicating if a vertex is upstream of the base vertex

    Parameters
    ----------
    vert_df : pd.DataFrame
        Vertex dataframe following format of `process_meshwork_to_dataframe` output
    base_lvl2_id : int
        Single l2 id to use as a point to separate upstream/downstream vertices
    downstream_column : str, optional
        Name of new column indicating vertices downstream of the point specified, by default "is_downstream"
    inclusive: bool, optional
        If True, includes the specified point. Default is True.

    Returns
    -------
    pd.DataFrame
        A dataframe with a boolean column indicating if vertices are downstream of the specified point
    """
    try:
        l2s_long = vert_df[LVL2_ID_COLUMN].explode()
        first_skind = l2s_long[l2s_long == base_lvl2_id].index[0]
    except:
        raise ValueError(f"Could not find vertex with level 2 id {base_lvl2_id}")

    if sk is None:
        sk = _skeleton_from_vertex_df(vert_df)

    vert_df[downstream_column] = False
    vert_df.loc[
        sk.downstream_nodes(first_skind, inclusive=inclusive), downstream_column
    ] = True

    return vert_df


def process_new_points(vertex_df: pd.DataFrame, seen_lvl2_ids: list) -> pd.DataFrame:
    "Check if any l2 id associated with a skeleton vertex is new"
    vertex_df[NEW_POINT_COLUMN] = True
    l2seen = vertex_df[LVL2_ID_COLUMN].explode().isin(seen_lvl2_ids)
    l2seen = l2seen[l2seen].index.unique()
    vertex_df.loc[l2seen, NEW_POINT_COLUMN] = False
    return vertex_df


def get_highest_overlap_lvl2_ids(root_id, timestamp, client):
    "Get level 2 ids for the past root with the highest overlap with the current root"
    if isinstance(timestamp, float):
        timestamp = datetime.fromtimestamp(timestamp)
    id_dict = client.chunkedgraph.get_past_ids(
        root_ids=root_id,
        timestamp_past=timestamp,
    )
    base_lvl2 = client.chunkedgraph.get_leaves(root_id, stop_layer=2)

    # As a heuristic, we start from the newest of the past roots because
    # it is likely to be a frequently edited object.
    past_ids = np.array(id_dict["past_id_map"].get(root_id, []))
    past_ids = past_ids[
        np.argsort(client.chunkedgraph.get_root_timestamps(past_ids))[::-1]
    ]

    relative_fracs = []
    past_lvl2 = {}
    for rid in past_ids:
        past_lvl2[rid] = client.chunkedgraph.get_leaves(rid, stop_layer=2)
        rel_frac = len(np.intersect1d(base_lvl2, past_lvl2[rid])) / len(base_lvl2)
        relative_fracs.append(rel_frac)
        # If the highest value seen is greater than what is left, stop
        if max(relative_fracs) > 1 - sum(relative_fracs):
            break

    highest_past = past_ids[np.argmax(relative_fracs)]
    return past_lvl2[highest_past]


def add_timestamp_relative_vertex(
    root_id: int,
    vertex_df: pd.DataFrame,
    client: caveclient.CAVEclient,
    horizon_timestamp: int,
) -> pd.DataFrame:
    "Add a column indicating True if vertex was not part of the best matching id at a previous timestamp"
    l2_previous_match = get_highest_overlap_lvl2_ids(root_id, horizon_timestamp, client)
    not_in_previous = ~vertex_df[LVL2_ID_COLUMN].explode().isin(l2_previous_match)

    # Treat everything as seen, then mark any that existed before as unseen
    vertex_df[NEW_TIMESTAMP_COLUMN] = False
    l2_newer_idx = not_in_previous[not_in_previous].index.unique()
    vertex_df.loc[l2_newer_idx, NEW_TIMESTAMP_COLUMN] = True
    return vertex_df


def filter_dataframe(
    root_id: int,
    vertex_df: pd.DataFrame,
    compartment_filter: Literal["axon", "dendrite", "all"] = None,
    restriction_direction: Optional[Literal["downstream-of", "upstream-of"]] = None,
    restriction_point: Optional[list] = None,
    only_new_lvl2: bool = False,
    only_after_timestamp: bool = False,
    horizon_timestamp: Optional[int] = None,
    max_branch_to_root: Optional[int] = None,
    max_distance_to_root: Optional[int] = None,
    client: Optional[caveclient.CAVEclient] = None,
    return_filtered: bool = True,
):
    qry_str = []
    if compartment_filter == "axon":
        qry_str.append(f"{IS_AXON_COLUMN} == True")
    elif compartment_filter == "dendrite":
        qry_str.append(f"{IS_AXON_COLUMN} == False")

    if max_branch_to_root is not None:
        qry_str.append(f"{NUM_BRANCH_TO_ROOT_COLUMN} <= {max_branch_to_root}")

    if max_distance_to_root is not None:
        qry_str.append(f"{DISTANCE_COLUMN} <= {max_distance_to_root}")

    if restriction_direction in RESTRICT_OPTIONS and restriction_point is not None:
        split_lvl2_id = chunk_tools.get_closest_lvl2_chunk(
            point=restriction_point,
            root_id=root_id,
            client=client,
            voxel_resolution=client.info.viewer_resolution(),
            radius=300,
        )
        if restriction_direction == "upstream-of":
            qry_str.append(f"is_downstream == False")
            vertex_df = add_downstream_column(
                vertex_df,
                split_lvl2_id,
                inclusive=False,
                downstream_column="is_downstream",
            )
        elif restriction_direction == "downstream-of":
            qry_str.append(f"is_downstream == True")
            vertex_df = add_downstream_column(
                vertex_df,
                split_lvl2_id,
                inclusive=True,
                downstream_column="is_downstream",
            )

    if only_new_lvl2:
        qry_str.append("is_new_point == True")
    if only_after_timestamp:
        vertex_df = add_timestamp_relative_vertex(
            root_id, vertex_df, client, horizon_timestamp
        )
        qry_str.append(f"{NEW_TIMESTAMP_COLUMN} == True")
    if len(qry_str) == 0 or not return_filtered:
        return vertex_df
    else:
        return vertex_df.query(" and ".join(qry_str))


def _make_skeleton_filter(
    root_id: int,
    sk: skeleton.Skeleton,
    vertex_df: pd.DataFrame,
    compartment_filter: Literal["axon", "dendrite", "all"] = None,
    restriction_direction: Optional[Literal["downstream-of", "upstream-of"]] = None,
    restriction_point: Optional[list] = None,
    max_branch_to_root: Optional[int] = None,
    max_distance_to_root: Optional[int] = None,
    only_new_lvl2: bool = False,
    only_after_timestamp: bool = False,
    horizon_timestamp: Optional[int] = None,
    client: Optional[caveclient.CAVEclient] = None,
) -> tuple:
    vertex_df = filter_dataframe(
        root_id,
        vertex_df,
        compartment_filter=compartment_filter,
        restriction_direction=restriction_direction,
        restriction_point=restriction_point,
        max_branch_to_root=max_branch_to_root,
        max_distance_to_root=max_distance_to_root,
        only_new_lvl2=only_new_lvl2,
        only_after_timestamp=only_after_timestamp,
        horizon_timestamp=horizon_timestamp,
        client=client,
        return_filtered=False,
    )

    mask = np.ones(len(sk.vertices), dtype=bool)
    if compartment_filter == "axon":
        mask &= vertex_df[IS_AXON_COLUMN].values
    elif compartment_filter == "dendrite":
        mask &= ~vertex_df[IS_AXON_COLUMN].values
    if restriction_direction in RESTRICT_OPTIONS and restriction_point is not None:
        if restriction_direction == "upstream-of":
            mask &= ~vertex_df["is_downstream"].values
        elif restriction_direction == "downstream-of":
            mask &= vertex_df["is_downstream"].values
    if only_new_lvl2:
        mask &= vertex_df[NEW_POINT_COLUMN].values
    if only_after_timestamp:
        mask &= vertex_df[NEW_TIMESTAMP_COLUMN].values
    if max_branch_to_root is not None:
        mask &= vertex_df[NUM_BRANCH_TO_ROOT_COLUMN] <= max_branch_to_root + 1
    if max_distance_to_root is not None:
        mask &= vertex_df[DISTANCE_COLUMN] <= max_distance_to_root
    return mask


def _interpolate_path(
    path,
    sk,
    step_size,
):
    path = path[::-1]
    if step_size is None:
        return sk.vertices[path]
    ds = sk.distance_to_root[path]
    ds_interp = np.linspace(
        ds[0],
        ds[-1],
        np.round((ds[-1] - ds[0]) / step_size).astype(int),
    )
    return np.vstack(
        [
            np.interp(ds_interp, ds, sk.vertices[path, 0]),
            np.interp(ds_interp, ds, sk.vertices[path, 1]),
            np.interp(ds_interp, ds, sk.vertices[path, 2]),
        ],
    ).T


def process_paths(
    root_id: int,
    vertex_df: pd.DataFrame,
    compartment_filter: Literal["axon", "dendrite", "all"] = None,
    restriction_direction: Optional[Literal["downstream-of", "upstream-of"]] = None,
    restriction_point: Optional[list] = None,
    max_branch_to_root: Optional[int] = None,
    max_distance_to_root: Optional[int] = None,
    only_new_lvl2: bool = False,
    only_after_timestamp: bool = False,
    horizon_timestamp: Optional[int] = None,
    step_size: Optional[int] = None,
    client: Optional[caveclient.CAVEclient] = None,
    min_path_length: Optional[float] = None,
    return_l2_ids: bool = False,
):
    sk = _skeleton_from_vertex_df(vertex_df)
    mask = _make_skeleton_filter(
        root_id,
        sk,
        vertex_df,
        compartment_filter=compartment_filter,
        restriction_direction=restriction_direction,
        restriction_point=restriction_point,
        max_branch_to_root=max_branch_to_root,
        max_distance_to_root=max_distance_to_root,
        only_new_lvl2=only_new_lvl2,
        only_after_timestamp=only_after_timestamp,
        horizon_timestamp=horizon_timestamp,
        client=client,
    )

    skm = sk.apply_mask(mask)
    paths = skm.cover_paths_with_parent()
    path_length = np.array(skm.path_length(paths))
    if min_path_length is None:
        min_path_length = 0

    if step_size:
        step_size_nm = 1000 * step_size
        interp_paths = np.vstack(
            [
                np.vstack(
                    [
                        _interpolate_path(path, skm, step_size_nm),
                        np.array([np.nan, np.nan, np.nan]).reshape((1, 3)),
                    ]
                )
                for path, pl in zip(paths, path_length)
                if pl > min_path_length
            ]
        )
    else:
        interp_paths = np.vstack(
            [
                np.vstack(
                    [
                        skm.vertices[path],
                        np.array([np.nan, np.nan, np.nan]).reshape((1, 3)),
                    ]
                )
                for path, pl in zip(paths, path_length)
                if pl > min_path_length
            ]
        )

    path_df = pd.DataFrame(
        np.concatenate([interp_paths[:-1], interp_paths[1:]], axis=1),
        columns=PATH_VERTEX_COLUMNS,
    ).dropna(axis=0)
    if return_l2_ids:
        return path_df, vertex_df[mask][LVL2_ID_COLUMN].explode().values
    else:
        return path_df, None
