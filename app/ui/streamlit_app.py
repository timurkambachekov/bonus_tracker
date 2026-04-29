from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_data import load_player_page_data
from app.ui.sections import (
    render_bonuses,
    render_contract,
    render_filters,
    render_player_details,
    render_seasonal_stats,
)


def main():
    st.set_page_config(page_title="bonus_tracker", layout="wide")
    st.title("Bonus Tracker")

    selected_player = render_filters()
    if not selected_player:
        return

    player, stats, contract, bonuses = load_player_page_data(selected_player.id)
    render_player_details(player)
    render_seasonal_stats(stats)
    render_contract(contract)
    if not contract:
        return
    render_bonuses(bonuses, stats)

if __name__ == "__main__":
    main()
