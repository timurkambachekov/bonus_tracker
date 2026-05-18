from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.frontend.auth import render_user_session, require_login
from app.frontend.page_data import load_player_page_data, load_squad_bonus_summary
from app.frontend.sections import (
    render_bonuses,
    render_contract,
    render_filters,
    render_player_details,
    render_seasonal_stats,
    render_squad_bonus_summary,
    render_squad_summary_filters,
)


def main():
    st.set_page_config(page_title="bonus_tracker", layout="wide")
    user = require_login()
    render_user_session(user)
    st.title("Bonus Tracker")

    player_tab, squad_tab = st.tabs(["Player Detail", "Squad Summary"])

    with player_tab:
        selected_player = render_filters(user)
        if selected_player:
            player, seasonal_stats, contract, bonuses = load_player_page_data(selected_player.id)
            render_player_details(player)
            render_seasonal_stats(seasonal_stats)
            render_contract(contract)
            if contract:
                render_bonuses(bonuses, seasonal_stats, contract)

    with squad_tab:
        selected_club = render_squad_summary_filters(user)
        if selected_club:
            summary_rows = load_squad_bonus_summary(selected_club.id)
            available_seasons = sorted(
                {int(row["Season"]) for row in summary_rows if row.get("Season") is not None},
                reverse=True,
            )
            if not available_seasons:
                st.info("No seasonal bonus summaries available for this squad.")
            else:
                selected_season = st.selectbox("Season", available_seasons, index=0)
                season_rows = [
                    row for row in summary_rows if int(row["Season"]) == int(selected_season)
                ]
                render_squad_bonus_summary(season_rows, selected_season)

if __name__ == "__main__":
    main()
