from typing import Optional
from caveclient.tools.caching import CachedClient
from caveclient import CAVEclient
import dash_mantine_components as dmc
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


def stash_dataframe(df, int64_cols=[], list_cols=[]):
    """Ready a dataframe for dcc.Store JSON format"""
    df = stringify_int64s(df, int64_cols)
    for col in list_cols:
        stringify_list(col, df)
    return df.to_dict("records")


def rehydrate_dataframe(rows, list_columns=[]):
    """Get a dataframe out of dcc.Store JSON format"""
    df = pd.DataFrame(rows)
    for col in list_columns:
        repopulate_list(col, df)
    return df


def _basic_button(
    text: str,
    is_filled: bool,
    button_id: Optional[str] = None,
    disabled: bool = False,
    **kwargs,
):
    return dmc.Button(
        text,
        color="indigo",
        style={
            "align-items": "center",
            "justify-content": "center",
        },
        loaderProps={"type": "dots"},
        variant="solid" if is_filled else "outline",
        id=button_id,
        fullWidth=True,
        disabled=disabled,
        **kwargs,
    )


def link_maker_button(
    text: str,
    button_id: Optional[str] = None,
    url: Optional[str] = None,
    disabled=False,
    **kwargs,
):
    if url is not None:
        return dmc.Anchor(
            _basic_button(
                text, button_id=button_id, is_filled=True, disabled=False, **kwargs
            ),
            href=url,
            target="_blank",
        )
    else:
        return _basic_button(
            text, button_id=button_id, is_filled=False, disabled=disabled, **kwargs
        )
