from typing import Optional
from caveclient.tools.caching import CachedClient
from caveclient import CAVEclient
import pandas as pd
import re


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
    auth_token: str,
):
    return CAVEclient(
        datastack_name=None,
        server_address=server_address,
        global_only=True,
        auth_token=auth_token,
    )


def stringify_int64s(df, stringify_cols=None):
    if stringify_cols is None:
        stringify_cols = [col for col in df.columns if re.search("_root_id$", col)]
    for col in stringify_cols:
        df[col] = df[col].astype(str)
    return df


def stringify_list(col, df):
    df[col] = df[col].apply(lambda x: str(x)[1:-1]).astype(str)
    return df


def repopulate_list(col, df):
    df[col] = df[col].apply(lambda x: [float(y) for y in x.split(",")]).astype(object)


def rehydrate_dataframe(rows, columns=[]):
    df = pd.DataFrame(rows)
    for col in columns:
        repopulate_list(col, df)
    return df
