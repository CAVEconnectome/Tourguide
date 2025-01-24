from typing import Optional
from ..guidebook_lib.lib_utils import make_client, make_global_client
import dash_mantine_components as dmc
import pandas as pd
import re
import numpy as np
from ..guidebook_lib.processing import LVL2_ID_COLUMN
from datetime import datetime, timezone, timedelta


def stringify_int64s(df, stringify_cols=None) -> pd.DataFrame:
    if stringify_cols is None:
        stringify_cols = [col for col in df.columns if re.search("_root_id$", col)]
    for col in stringify_cols:
        df[col] = df[col].astype(str)
    return df


def stringify_list(col, df) -> pd.DataFrame:
    df[col] = df[col].apply(lambda x: str(x)[1:-1]).astype(str)
    return df


def repopulate_list(col, df) -> None:
    df[col] = df[col].apply(lambda x: [int(y) for y in x.split(",")]).astype(object)


def stash_dataframe(df, int64_cols=[], list_cols=[]) -> list:
    """Ready a dataframe for dcc.Store JSON format"""
    df = stringify_int64s(df, int64_cols)
    for col in list_cols:
        stringify_list(col, df)
    return df.to_dict("records")


def rehydrate_dataframe(rows, list_columns=[]) -> pd.DataFrame:
    """Get a dataframe out of dcc.Store JSON format"""
    df = pd.DataFrame(rows)
    for col in list_columns:
        repopulate_list(col, df)
    return df


def stash_id_list(ids) -> list:
    "Return a list of int64s as a string"
    return [str(x) for x in ids]


def rehydrate_id_list(ids) -> list:
    "Return a rehydrated list of int64s stored as strings"
    return [int(x) for x in ids]


def update_seen_id_list(lvl2_ids: list, vertex_df: pd.DataFrame) -> list:
    "Return a list of unique lvl2_ids from the vertex dataframe and a list of ids"
    return (
        np.unique(
            np.concatenate(
                [
                    lvl2_ids,
                    vertex_df[LVL2_ID_COLUMN].explode().values,
                ]
            )
        )
        .astype(str)
        .tolist()
    )


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
    "Return a button that opens a new tab if a URL is provided"
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


def convert_time_string_to_utc(timestamp, offset):
    "Convert datetime picker string to UTC timestamp"
    t = datetime.fromisoformat(timestamp)
    delta_t = timedelta(minutes=offset)
    t_utc = (t + delta_t).replace(tzinfo=timezone.utc)
    return t_utc.timestamp()
