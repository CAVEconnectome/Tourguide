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
                dmc.Radio(
                    "Whole Cell",
                    mt="5px",
                    value="all-cell",
                    id="radio-all-cell",
                ),
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
        value="all-cell",
        mb=10,
        size="sm",
    )

    split_point_option = dmc.Stack(
        [
            dmc.Select(
                id="split-point-select",
                label="Split at point:",
                data=[
                    {"label": "No split", "value": "no-split"},
                    {"label": "Upstream of", "value": "upstream-of"},
                    {"label": "Downstream of", "value": "downstream-of"},
                ],
                value="no-split",
                mb=10,
            ),
            dmc.TextInput(
                id="split-point-input",
                description="Use standard neuroglancer coordinates for the dataset",
            ),
        ]
    )

    new_point_selector = dmc.Stack(
        [
            dmc.Checkbox(
                "Only show points not previously seen during browser session",
                mt="10px",
                id="new-point-checkbox",
            ),
            dmc.Space(h=5),
            dmc.Center(
                dmc.Button(
                    "Reset Unseen Points",
                    id="clear-history-modal-toggle",
                    color="red",
                    size="xs",
                    variant="outline",
                    w="50%",
                    justify="center",
                )
            ),
            dmc.Modal(
                id="clear-history-modal",
                children=[
                    dmc.Title("Reset Unseen Points", order=4),
                    dmc.Space(h=4),
                    dmc.Text(
                        "Are you sure you want to clear your history of seen points?"
                    ),
                    dmc.Space(h=4),
                    dmc.Text(id="previously-unseen-message", c="gray"),
                    dmc.Text(
                        f"Points will clear automatically when you quit this browser.",
                        c="gray",
                        fs="xs",
                    ),
                    dmc.Space(h=20),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Clear History", color="red", id="clear-history-confirm"
                            ),
                            dmc.Button(
                                "Cancel",
                                color="gray",
                                id="clear-history-cancel",
                                variant="outline",
                            ),
                        ],
                        justify="flex-end",
                    ),
                ],
            ),
        ]
    )

    time_restriction = dmc.Stack(
        [
            dmc.Checkbox(
                "Only points added to main object since...",
                id="use-time-restriction",
                checked=False,
                mt="10px",
            ),
            dmc.DateTimePicker(
                id="restriction-datetime",
                label="Previous Timepoint:",
                value=datetime.now(),
                disabled=True,
            ),
        ]
    )

    restriction_options = dmc.SimpleGrid(
        [
            dmc.Card(
                [
                    dmc.CardSection(
                        dmc.Text(
                            "Cell Filters", fw=600, bg="var(--mantine-color-blue-1)"
                        ),
                        withBorder=True,
                        inheritPadding=True,
                    ),
                    dmc.SimpleGrid(
                        [
                            compartment_radio,
                            split_point_option,
                        ],
                        cols=2,
                    ),
                ],
                py="sx",
            ),
            dmc.Card(
                [
                    dmc.CardSection(
                        dmc.Text(
                            "Time Filters", fw=600, bg="var(--mantine-color-teal-1)"
                        ),
                        withBorder=True,
                        inheritPadding=True,
                    ),
                    dmc.SimpleGrid(
                        [
                            new_point_selector,
                            time_restriction,
                        ],
                        cols=2,
                    ),
                ],
                py="sx",
            ),
        ],
        cols=2,
        spacing="md",
        mt="15px",
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
                    html.Div(
                        link_maker_button(
                            "Generate Branch Point Link",
                            button_id="branch-point-link-button",
                            disabled=True,
                        ),
                        id="branch-point-link-card",
                    ),
                    span=4,
                ),
                dmc.GridCol(
                    html.Div(
                        link_maker_button(
                            "Generate End and Branch Point Link",
                            button_id="branch-end-point-link-button",
                            disabled=True,
                        ),
                        id="branch-end-point-link-card",
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
            dcc.Location("url", refresh=False),
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
            dmc.Container(restriction_options, fluid=True, w="80%"),
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
            dcc.Store(
                id="seen-lvl2-ids",
                data=[],
                storage_type="session",
            ),
            dcc.Store(id="curr-root-id"),
        ]
    )
    return layout


dash.register_page(
    __name__,
    path_template="datastack/<datastack_name>/",
    title=title,
)
