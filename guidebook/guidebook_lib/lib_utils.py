import flask
from typing import Optional
from caveclient import CAVEclient
from caveclient.tools.caching import CachedClient


def make_client(
    datastack_name: str,
    server_address: Optional[str] = None,
    auth_token: Optional[str] = None,
):
    "Generate the appropriate CAVEclient with info caching"
    return CachedClient(
        datastack_name=datastack_name,
        server_address=server_address,
        auth_token=auth_token,
    )


def make_global_client(
    server_address: str,
    auth_token: Optional[str] = None,
):
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
