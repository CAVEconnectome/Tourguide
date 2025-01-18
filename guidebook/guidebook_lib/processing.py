import numpy as np
from meshparty import meshwork, skeleton
from ..guidebook_app.utils import make_client
from typing import Optional
import pandas as pd
from scipy import sparse

VERTEX_POINT = "pt"
VERTEX_COLUMNS = [f"{VERTEX_POINT}_{suf}" for suf in ["x", "y", "z"]]
BRANCH_GROUP_COLUMN = "branch_group"
DISTANCE_COLUMN = "distance_to_root"
IS_AXON_COLUMN = "is_axon"
PARENT_COLUMN = "parent"
LVL2_ID_COLUMN = "lvl2_id"
END_POINT_COLUMN = "is_end"
BRANCH_POINT_COLUMN = "is_branch"
ROOT_COLUMN = "is_root"


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
            LVL2_ID_COLUMN: l2df.groupby("skind")[LVL2_ID_COLUMN].agg(list),
        }
    )
    vert_df[END_POINT_COLUMN] = False
    vert_df.loc[nrn.skeleton.end_points, END_POINT_COLUMN] = True

    vert_df[BRANCH_POINT_COLUMN] = False
    vert_df.loc[nrn.skeleton.branch_points, BRANCH_POINT_COLUMN] = True

    vert_df[ROOT_COLUMN] = False
    vert_df.loc[int(nrn.skeleton.root), ROOT_COLUMN] = True

    return vert_df


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


def add_downstream_column(
    vert_df: pd.DataFrame,
    base_lvl2_id: int,
    downstream_column: str = "is_downstream",
    inclusive: bool = True,
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
        A dataframe with a boolean column indicating if vertices are
    """
    try:
        first_skind = (
            vert_df.explode(LVL2_ID_COLUMN)
            .query(f"{LVL2_ID_COLUMN}=={base_lvl2_id}")[PARENT_COLUMN]
            .values[0]
        )
    except:
        raise ValueError(f"Could not find vertex with level 2 id {base_lvl2_id}")

    sk = skeleton.Skeleton(
        vertices=vert_df[VERTEX_COLUMNS].values,
        edges=vert_df.query(f"{PARENT_COLUMN}!=-1")[PARENT_COLUMN].reset_index().values,
        root=int(vert_df.query(PARENT_COLUMN).index[0]),
    )

    vert_df[downstream_column] = False
    vert_df.loc[
        sk.downstream_nodes(first_skind, inclusive=inclusive), downstream_column
    ] = True

    return vert_df


def update_seen_id_list(lvl2_ids: list, vertex_df: pd.DataFrame) -> list:
    return np.unique(
        np.concatenate(
            [
                lvl2_ids,
                vertex_df[LVL2_ID_COLUMN].explode().values,
            ]
        )
    ).tolist()
