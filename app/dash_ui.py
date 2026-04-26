import os

import dash
import requests
from dash import Input, Output, dash_table, dcc, html
API_BASE_URL = os.getenv("BONUS_TRACKER_API_URL", "http://127.0.0.1:8000")

app = dash.Dash(__name__, title="bonus_tracker")


def fetch_json(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def load_dataset():
    clubs = fetch_json("/api/clubs")["items"]
    players = fetch_json("/api/players?limit=2000")["items"]
    return clubs, players


app.layout = html.Div(
    [
        dcc.Store(id="data-store"),
        dcc.Store(id="player-detail-store"),
        dcc.Interval(id="bootstrap", interval=100, max_intervals=1),
        html.Div(
            [
                html.Div("RPL Bonus Tracker", className="eyebrow"),
                html.H1("Club, Player, Contract"),
                html.P(
                    "Choose a club, then a player, and inspect the player profile, season stats, contract terms, and bonuses from the backend.",
                    className="lede",
                ),
            ],
            className="hero",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Club"),
                        dcc.Dropdown(id="club-filter", placeholder="Choose a club"),
                    ],
                    className="control",
                ),
                html.Div(
                    [
                        html.Label("Player"),
                        dcc.Dropdown(id="player-filter", placeholder="Choose a player"),
                    ],
                    id="player-control",
                    className="control",
                    style={"display": "none"},
                ),
            ],
            className="controls",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H2("Player Details"),
                        html.Div(id="player-details", className="detail-grid"),
                    ],
                    className="panel detail-panel",
                ),
                html.Div(
                    [
                        html.H2("Season Stats"),
                        dash_table.DataTable(
                            id="stats-table",
                            page_size=15,
                            style_table={"overflowX": "auto"},
                            style_cell={"textAlign": "left", "padding": "10px", "fontFamily": "Georgia, serif"},
                            style_header={"backgroundColor": "#f5efe4", "fontWeight": "bold"},
                        ),
                    ],
                    className="panel table-panel",
                ),
                html.Div(
                    [
                        html.H2("Contract Terms"),
                        html.Div(id="contract-terms-text", className="detail-grid"),
                    ],
                    className="panel table-panel",
                ),
                html.Div(
                    [
                        html.H2("Bonuses"),
                        html.Div(id="bonuses-text", className="detail-grid"),
                    ],
                    className="panel table-panel",
                ),
            ],
            className="tables-grid",
        ),
    ],
    className="page",
)


@app.callback(
    Output("data-store", "data"),
    Output("club-filter", "options"),
    Input("bootstrap", "n_intervals"),
)
def bootstrap(_):
    clubs, players = load_dataset()
    options = [{"label": club["club_slug"], "value": club["club_slug"]} for club in clubs]
    return {"clubs": clubs, "players": players}, options


@app.callback(
    Output("player-control", "style"),
    Output("player-filter", "options"),
    Output("player-filter", "value"),
    Input("data-store", "data"),
    Input("club-filter", "value"),
)
def player_options(data, club_filter):
    if not data or not club_filter:
        return {"display": "none"}, [], None
    players = data["players"]
    players = [row for row in players if row.get("club_slug") == club_filter]
    options = [
        {"label": row.get("player_name") or f"Player {row.get('id')}", "value": row.get("id")}
        for row in players
    ]
    return {"display": "block"}, options, None


@app.callback(
    Output("player-detail-store", "data"),
    Input("player-filter", "value"),
)
def load_player_detail(player_id):
    if not player_id:
        return None
    return fetch_json(f"/api/players/{player_id}")


@app.callback(
    Output("player-details", "children"),
    Output("stats-table", "data"),
    Output("stats-table", "columns"),
    Output("contract-terms-text", "children"),
    Output("bonuses-text", "children"),
    Input("data-store", "data"),
    Input("club-filter", "value"),
    Input("player-detail-store", "data"),
)
def render_dashboard(data, club_filter, player_detail):
    if not data:
        return [], [], [], [], []

    if not player_detail:
        return [], [], [], [], []

    detail_children = []
    stats_rows = []
    contract_terms_children = []
    bonus_children = []
    player = player_detail["player"]
    detail_children = [
        html.Div(
            [
                html.Div("Player", className="summary-label"),
                html.Div(player.get("player_name") or "", className="summary-value"),
            ],
            className="summary-card",
        ),
        html.Div(
            [
                html.Div("Club", className="summary-label"),
                html.Div(player.get("club_slug") or "-", className="summary-value"),
            ],
            className="summary-card",
        ),
        html.Div(
            [
                html.Div("Position", className="summary-label"),
                html.Div(player.get("position") or "-", className="summary-value"),
            ],
            className="summary-card",
        ),
        html.Div(
            [
                html.Div("Nationality", className="summary-label"),
                html.Div(player.get("nationality") or "-", className="summary-value"),
            ],
            className="summary-card",
        ),
        html.Div(
            [
                html.Div("Date of Birth", className="summary-label"),
                html.Div(player.get("date_of_birth") or "-", className="summary-value"),
            ],
            className="summary-card",
        ),
        html.Div(
            [
                html.Div("Height (m)", className="summary-label"),
                html.Div(player.get("height_m") or "-", className="summary-value"),
            ],
            className="summary-card",
        ),
        html.Div(
            [
                html.Div("Foot", className="summary-label"),
                html.Div(player.get("foot") or "-", className="summary-value"),
            ],
            className="summary-card",
        ),
        html.Div(
            [
                html.Div("Market Value EUR", className="summary-label"),
                html.Div(player.get("market_value_eur") or "-", className="summary-value"),
            ],
            className="summary-card",
        ),
    ]
    stats_rows = player_detail["stats"]
    for contract in player_detail["contracts"]:
        contract_terms_children.append(
            html.Div(
                [
                    html.Div(
                        f"Club: {contract.get('club_slug') or '-'}",
                        className="summary-label",
                    ),
                    html.Div(
                        f"Base salary: {contract.get('base_salary') or '-'} RUB per month",
                        className="summary-value",
                    ),
                    html.Div(
                        f"Term: {contract.get('contract_start') or '-'} — {contract.get('contract_end') or '-'}",
                        className="summary-value",
                    ),
                ],
                className="summary-card",
            )
        )
        for bonus in contract.get("bonuses", []):
            conditions = []
            if bonus.get("games"):
                conditions.append(f"games >= {bonus['games']}")
            if bonus.get("minutes"):
                conditions.append(f"minutes >= {bonus['minutes']}")
            if bonus.get("goals"):
                conditions.append(f"goals >= {bonus['goals']}")
            if bonus.get("assists"):
                conditions.append(f"assists >= {bonus['assists']}")
            if not conditions:
                conditions.append("no threshold")

            bonus_children.append(
                html.Div(
                    [
                        html.Div(
                            f"Contract #{contract.get('id')}",
                            className="summary-label",
                        ),
                        html.Div(
                            f"Type: {bonus.get('bonus_type') or '-'}",
                            className="summary-value",
                        ),
                        html.Div(
                            f"Competition: {bonus.get('competition') or '-'}",
                            className="summary-value",
                        ),
                        html.Div(
                            f"Condition: {', '.join(conditions)}",
                            className="summary-value",
                        ),
                        html.Div(
                            f"Bonus value: {bonus.get('bonus_value') or 0} RUB",
                            className="summary-value",
                        ),
                    ],
                    className="summary-card",
                )
            )

    if not contract_terms_children:
        contract_terms_children = [
            html.Div(
                "No contract terms are loaded for the selected player.",
                className="summary-label",
            )
        ]

    if not bonus_children:
        bonus_children = [
            html.Div(
                "No bonuses are loaded for the selected player.",
                className="summary-label",
            )
        ]

    stats_columns = [
        {"name": "Season", "id": "season"},
        {"name": "Apps", "id": "appearances"},
        {"name": "Goals", "id": "goals"},
        {"name": "Assists", "id": "assists"},
        {"name": "Minutes", "id": "minutes_played"},
        {"name": "PPG", "id": "ppg"},
    ]

    return (
        detail_children,
        stats_rows,
        stats_columns,
        contract_terms_children,
        bonus_children,
    )


def main():
    app.run(debug=True, port=8050)


if __name__ == "__main__":
    main()
