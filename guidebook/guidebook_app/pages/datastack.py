import dash
from dash import html, dcc
import dash_bootstrap_components as dbc


def title(datastack_name=None):
    return f"Guidebook Morphology Explorer: {datastack_name}"


def layout(**kwargs):
    header_row = dbc.Row(
        [
            dbc.Col(
                html.Div(id="header-bar", children="Header Bar"),
                width={"size": 12},
            ),
        ],
    )

    query_section = html.Div(
        children=[
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.P("Root ID:"),
                            dbc.Input(
                                id="guidebook-root-id",
                                type="text",
                            ),
                        ],
                        width={"size": 3, "offset": 1},
                        align="end",
                    ),
                    dbc.Col(
                        dbc.Button(
                            children="Submit",
                            id="submit-button",
                            color="primary",
                            style={"font-size": "18px"},
                        ),
                        width={"size": 1},
                        align="center",
                    ),
                    dbc.Col(
                        dcc.Loading(
                            id="main-loading",
                            children=html.Div(
                                id="main-loading-placeholder", children=""
                            ),
                            type="default",
                            style={"transform": "scale(0.8)"},
                        ),
                        align="center",
                        width={"size": 1},
                    ),
                ],
                justify="start",
            )
        ]
    )

    message_row = dbc.Alert(
        id="message-text",
        children="Please select a root id and press Submit",
        color="info",
    )

    link_section = html.Div(
        dbc.Row(
            [
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Div(
                                    children=[
                                        dbc.Button(
                                            "Generate End Point Link",
                                            id="end-point-link-button",
                                            color="secondary",
                                            className="d-grid gap-2 col-6 mx-auto",
                                            style={
                                                "align-items": "center",
                                                "justify-content": "center",
                                            },
                                        ),
                                    ]
                                ),
                                dbc.Spinner(
                                    html.Div(
                                        "", id="end-point-link", className="card-text"
                                    ),
                                    size="sm",
                                ),
                            ]
                        )
                    ]
                ),
            ],
        )
    )

    layout = [
        dcc.Location("url"),
        header_row,
        dbc.Container(query_section),
        dbc.Container(message_row),
        html.Hr(),
        dbc.Container(link_section),
        html.Hr(),
        dcc.Store(id="vertex-df"),
        dcc.Store(id="seen-lvl2-ids", data=[], storage_type="session"),
        dcc.Store(id="curr-root-id"),
    ]
    return layout


dash.register_page(
    __name__,
    path_template="datastack/<datastack_name>/",
    title=title,
)
