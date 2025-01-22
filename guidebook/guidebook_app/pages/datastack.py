import dash
from dash import html, dcc
import dash_mantine_components as dmc
from ..utils import link_maker_button
from datetime import datetime


def title(datastack_name=None):
    return f"Guidebook Morphology Explorer: {datastack_name}"


def layout(**kwargs):
    header_row = dmc.Container(
        html.Div(id="header-bar"),
        fluid=True,
        bg="var(--mantine-color-indigo-5)",
        c="white",
    )

    query_section = dmc.Grid(
        [
            dmc.GridCol(
                dmc.NumberInput(
                    id="guidebook-root-id",
                    placeholder="Enter a root id",
                    hideControls=True,
                    allowNegative=False,
                    allowDecimal=False,
                    label="Root ID:",
                ),
                span=5,
            ),
            dmc.GridCol(
                dmc.Button(
                    children="Submit",
                    id="submit-button",
                    color="var(--mantine-color-indigo-7)",
                    # loaderProps={"type": "dots"},
                ),
                span=1,
            ),
        ],
        justify="start",
        align="center",
    )

    message_row = dmc.Alert(
        id="message-text",
        children="Please enter a root id and press Submit",
        color="violet",
    )

    compartment_radio = dmc.RadioGroup(
        id="compartment-radio",
        label="Predicted Compartment:",
        children=dmc.Stack(
            [
                dmc.Radio("Whole Cell", value="all-cell"),
                dmc.Radio(
                    "Axon Only",
                    id="radio-axon",
                    value="axon",
                    disabled=True,
                ),
                dmc.Radio(
                    "Dendrite Only",
                    id="radio-dendrite",
                    value="dendrite",
                    disabled=True,
                ),
            ]
        ),
        deselectable=True,
        value="all-cell",
        mb=10,
        size="sm",
    )

    split_point_option = dmc.Stack(
        [
            dmc.RadioGroup(
                id="split-point-radio",
                label="Split at point:",
                children=dmc.Stack(
                    [
                        dmc.Radio("Upstream of", value="upstream-of"),
                        dmc.Radio("Downstream of", value="downstream-of"),
                    ]
                ),
                deselectable=True,
                size="sm",
            ),
            dmc.TextInput(
                id="split-point-input",
            ),
        ]
    )

    new_point_selector = dmc.Checkbox(
        "Only new points in session", id="new-point-checkbox"
    )

    time_restriction = dmc.Stack(
        [
            dmc.Checkbox(
                "Only points since...", id="use-time-restriction", checked=False
            ),
            dmc.DateTimePicker(
                id="restriction-datetime",
                label="Date and time",
                valueFormat="DD MMM YYYY hh:mm A",
                value=datetime.now(),
                disabled=True,
            ),
        ]
    )

    restriction_options = dmc.Grid(
        [
            dmc.GridCol(
                compartment_radio,
                span=2,
            ),
            dmc.GridCol(
                split_point_option,
                span=2,
            ),
            dmc.GridCol(
                new_point_selector,
                span=2,
            ),
            dmc.GridCol(
                time_restriction,
                span=2,
            ),
        ],
    )

    restriction_row = dmc.Accordion(
        children=[
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        "Restrictions", style={"font-size": "1.25rem"}
                    ),
                    dmc.AccordionPanel(children=restriction_options),
                ],
                value="restriction-accordion",
            )
        ]
    )

    point_links = dmc.Container(
        dmc.Grid(
            [
                dmc.GridCol(
                    html.Div(
                        children=link_maker_button(
                            "Generate End Point Link",
                            button_id="end-point-link-button",
                            disabled=True,
                        ),
                        id="end-point-link-card",
                    ),
                    span=4,
                ),
                dmc.GridCol(
                    link_maker_button(
                        "Generate Branch Point Link",
                        button_id="branch-point-link-button",
                        disabled=True,
                    ),
                    span=4,
                ),
                dmc.GridCol(
                    link_maker_button(
                        "Generate End and Branch Point Link",
                        button_id="end-branch-point-link-button",
                        disabled=True,
                    ),
                    span=4,
                ),
            ],
        ),
        fluid=True,
    )

    path_links = dmc.Container("path links")

    output_tabs = dmc.Tabs(
        [
            dmc.TabsList(
                [
                    dmc.TabsTab("Point Links", value="points_tab"),
                    dmc.TabsTab("Path Links", value="paths_tab"),
                ]
            ),
            dmc.TabsPanel(point_links, value="points_tab"),
            dmc.TabsPanel(path_links, value="paths_tab"),
        ],
        variant="outline",
        value="points_tab",
        orientation="vertical",
        placement="left",
    )

    layout = dmc.MantineProvider(
        children=[
            dcc.Location("url"),
            dcc.Interval(
                id="load-interval",
                n_intervals=0,
                max_intervals=0,
                interval=1,
            ),  # Used to trigger the timezone offset callback
            header_row,
            dmc.Container(query_section, fluid=True, w="80%"),
            dmc.Container(message_row, fluid=True, w="80%"),
            dmc.Container(dmc.Divider(), fluid=True, w="80%"),
            dmc.Container(restriction_row, fluid=True, w="80%"),
            dmc.Container(dmc.Divider(), fluid=True, w="80%"),
            dmc.Container(
                dmc.Text(
                    "Links and Outputs",
                    style={"font-size": "1.25rem"},
                ),
                fluid=True,
                w="80%",
            ),
            dmc.Container(output_tabs, fluid=True, w="80%"),
            dcc.Store(id="timezone-offset"),
            dcc.Store(id="vertex-df"),
            dcc.Store(id="seen-lvl2-ids", data=[], storage_type="session"),
            dcc.Store(id="curr-root-id"),
        ]
    )
    return layout


dash.register_page(
    __name__,
    path_template="datastack/<datastack_name>/",
    title=title,
)
