import numpy as np
from meshparty import meshwork, skeleton
from ..guidebook_app.utils import make_client
from typing import Optional
import pandas as pd

VERTEX_POINT = "pt"
VERTEX_COLUMNS = [f"{VERTEX_POINT}_{suf}" for suf in ["x", "y", "z"]]


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
            "is_axon": is_axon,
            "parent": nrn.skeleton.parent_nodes(nrn.skeleton_indices),
            "lvl2_id": l2df.groupby("skind")["lvl2_id"].agg(list),
        }
    )
    vert_df["is_end_point"] = False
    vert_df.loc[nrn.skeleton.end_points, "is_end_point"] = True

    vert_df["is_branch_point"] = False
    vert_df.loc[nrn.skeleton.branch_points, "is_branch_point"] = True

    vert_df["is_root"] = False
    vert_df.loc[int(nrn.skeleton.root), "is_root"] = True

    return vert_df


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
            vert_df.explode("lvl2_id")
            .query(f"lvl2_id=={base_lvl2_id}")["parent"]
            .values[0]
        )
    except:
        raise ValueError(f"Could not find vertex with level 2 id {base_lvl2_id}")

    sk = skeleton.Skeleton(
        vertices=vert_df[["x", "y", "z"]].values,
        edges=vert_df.query("parent!=-1")["parent"].reset_index().values,
        root=int(vert_df.query("is_root").index[0]),
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
                vertex_df["lvl2_id"].explode().values,
            ]
        )
    ).tolist()
