import datetime
from typing import Optional
from urllib.parse import urlparse

import flask
import numpy as np
from caveclient import CAVEclient
from caveclient.base import ServerIncompatibilityError
from caveclient.tools.caching import CachedClient


def make_client(
    datastack_name: str,
    server_address: Optional[str] = None,
    auth_token: Optional[str] = None,
):
    "Generate the appropriate CAVEclient with info caching"
    if len(urlparse(server_address).scheme) == 0:
        server_address = f"https://{server_address}"
    return CachedClient(
        datastack_name=datastack_name,
        server_address=server_address,
        auth_token=auth_token,
    )


def make_global_client(
    server_address: str,
    auth_token: Optional[str] = None,
):
    if len(urlparse(server_address).scheme) == 0:
        server_address = f"https://{server_address}"
    return CAVEclient(
        datastack_name=None,
        server_address=server_address,
        global_only=True,
        auth_token=auth_token,
    )


def process_point_string(pt_str):
    """Take text input of 3d point and convert to a list of values. Validate that it is 3d."""
    pt = [int(x) for x in pt_str.split(",")]
    if len(pt) != 3:
        raise ValueError("Point string must have 3 comma-separated values")
    else:
        return pt


def suggest_latest_roots_robust(client, root_id, timestamp=None):
    """Use the chunkedgraph to suggest current roots for a given root_id and timestamp."""
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc)

    curr_ids = client.chunkedgraph.get_latest_roots(root_id, timestamp=timestamp)
    if root_id in curr_ids:
        return root_id
    # This should not be needed, but until the PCG is fixed this is important
    is_current = client.chunkedgraph.is_latest_roots(curr_ids, timestamp=timestamp)
    curr_ids = curr_ids[is_current]

    delta_layers = 4
    stop_layer = (
        client.chunkedgraph.segmentation_info.get("graph", {}).get("n_layers", 6)
        - delta_layers
    )
    stop_layer = max(1, stop_layer)

    chunks_orig = client.chunkedgraph.get_leaves(root_id, stop_layer=stop_layer)
    while len(chunks_orig) == 0:
        stop_layer -= 1
        if stop_layer == 1:
            raise ValueError(
                f"There were no children for root_id={root_id} at level 2, something is wrong with the chunkedgraph"
            )
        chunks_orig = client.chunkedgraph.get_leaves(root_id, stop_layer=stop_layer)

    chunk_list = np.array(
        [
            len(
                np.intersect1d(
                    chunks_orig,
                    client.chunkedgraph.get_leaves(oid, stop_layer=stop_layer),
                    assume_unique=True,
                )
            )
            / len(chunks_orig)
            for oid in curr_ids
        ]
    )
    order = np.argsort(chunk_list)[::-1]
    return curr_ids[order][0]
