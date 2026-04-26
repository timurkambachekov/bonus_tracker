import os
from datetime import date, datetime

import requests
import streamlit as st

API_BASE_URL = os.getenv("BONUS_TRACKER_API_URL", "http://127.0.0.1:8000")


def fetch_json(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False)
def load_dataset():
    clubs = fetch_json("/api/clubs")["items"]
    players = fetch_json("/api/players?limit=2000")["items"]
    return clubs, players


@st.cache_data(show_spinner=False)
def load_player_detail(player_id: int):
    return fetch_json(f"/api/players/{player_id}")


def format_money(value):
    if value in (None, ""):
        return "-"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def format_date(value):
    if value in (None, ""):
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    try:
        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y")
    except ValueError:
        return str(value)


def render_contract(contract):
    club_name = contract.get("club_name") or contract.get("club_slug") or "-"
    st.write(f"**Club:** {club_name}")
    st.write(f"**Base salary:** {format_money(contract.get('base_salary'))} RUB/month")
    st.write(
        f"**Term:** {format_date(contract.get('contract_start'))} — {format_date(contract.get('contract_end'))}"
    )
    st.write(f"**Total payout from bonuses:** {format_money(contract.get('total_payout_value') or 0)} RUB")

def bonus_sentence(bonus):
    amount = f"{format_money(bonus.get('bonus_value') or 0)} RUB"
    competition = bonus.get("competition") or "official"
    bonus_type = bonus.get("bonus_type") or "bonus"
    games = bonus.get("games") or 0
    starts = bonus.get("starts") or 0
    minutes = bonus.get("minutes") or 0
    goals = bonus.get("goals") or 0
    assists = bonus.get("assists") or 0
    conditions = []
    if games:
        conditions.append(f"{games} matchday squad inclusion{'s' if games != 1 else ''}")
    if starts:
        conditions.append(f"{starts} start{'s' if starts != 1 else ''}")
    if minutes:
        conditions.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if goals:
        conditions.append(f"{goals} goal{'s' if goals != 1 else ''}")
    if assists:
        conditions.append(f"{assists} assist{'s' if assists != 1 else ''}")

    if goals and assists:
        trigger = "each goal-plus-assist point"
    elif len(conditions) == 1:
        trigger = conditions[0]
    elif conditions:
        trigger = ", ".join(conditions[:-1]) + f" and {conditions[-1]}"
    else:
        trigger = "the relevant performance condition"

    type_prefix = {
        "seasonal": "Seasonal bonus",
        "one_time": "One-time bonus",
        "repeatable": "Repeatable bonus",
    }.get(bonus_type, "Bonus")

    return (
        f"{type_prefix}: {amount} for {trigger} in {competition} competition "
        f"for the first team."
    )


def render_bonus(contract_id, bonus):
    st.write(f"**Contract:** #{contract_id}")
    st.write(bonus_sentence(bonus))
    st.write(f"**Payout:** {format_money(bonus.get('payout_value') or 0)} RUB")
    progress = bonus.get("progress")
    if progress:
        ratio = progress.get("completion_ratio")
        ratio_text = f"{int(ratio * 100)}%" if ratio is not None else "n/a"
        status = "achieved" if progress.get("achieved") else "in progress"
        season = progress.get("season") or "-"
        if bonus.get("bonus_type") == "repeatable":
            times_achieved = progress.get("times_achieved")
            times_text = times_achieved if times_achieved is not None else "n/a"
            st.caption(
                f"Season {season} | Progress: {ratio_text} | Times achieved: {times_text} | Status: {status}"
            )
        else:
            st.caption(f"Season {season} | Progress: {ratio_text} | Status: {status}")


def main():
    st.set_page_config(page_title="bonus_tracker", layout="wide")
    st.markdown(
        """
        <style>
        [data-testid="stMetricValue"] {
            white-space: normal;
            overflow-wrap: anywhere;
            line-height: 1.1;
        }
        [data-testid="stMetricLabel"] {
            white-space: normal;
            overflow-wrap: anywhere;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Player Bonus Tracker")
    st.caption(
        "Choose a club, then a player, and inspect the player profile, season stats, contract terms, and bonuses."
    )

    try:
        clubs, players = load_dataset()
    except requests.RequestException as exc:
        st.error(f"Could not load backend data: {exc}")
        return

    club_options = [""] + [club["club_slug"] for club in clubs]
    club_label_map = {
        club["club_slug"]: (club.get("club_name") or club["club_slug"])
        for club in clubs
    }
    selected_club = st.selectbox(
        "Club",
        club_options,
        format_func=lambda value: "Choose a club" if not value else club_label_map.get(value, value),
    )

    if not selected_club:
        return

    filtered_players = [player for player in players if player.get("club_slug") == selected_club]
    player_map = {
        player.get("player_name") or "Unknown": player["id"]
        for player in filtered_players
    }

    selected_player_label = st.selectbox(
        "Player",
        [""] + list(player_map.keys()),
        format_func=lambda value: value or "Choose a player",
    )

    if not selected_player_label:
        return

    player_id = player_map[selected_player_label]
    try:
        payload = load_player_detail(player_id)
    except requests.RequestException as exc:
        st.error(f"Could not load player detail: {exc}")
        return

    player = payload["player"]
    totals = payload.get("totals", {})

    st.subheader(player.get("player_name") or "Player")
    detail_cols = st.columns(4)
    detail_items = [
        ("Club", player.get("club_name") or player.get("club_slug") or "-"),
        ("Position", player.get("position") or "-"),
        ("Nationality", player.get("nationality") or "-"),
        ("Date of Birth", format_date(player.get("date_of_birth"))),
        ("Height (m)", player.get("height_m") or "-"),
        ("Foot", player.get("foot") or "-"),
        ("Market Value EUR", format_money(player.get("market_value_eur"))),
        ("Total Bonus Payout", format_money(totals.get("total_payout_value") or 0)),
    ]
    for index, (label, value) in enumerate(detail_items):
        with detail_cols[index % 4]:
            st.metric(label, value)

    st.subheader("Season Stats")
    stats_rows = payload["stats"]
    if stats_rows:
        st.dataframe(stats_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No season stats are loaded for the selected player.")

    st.subheader("Contract Terms")
    contracts = payload["contracts"]
    if contracts:
        for contract in contracts:
            with st.container(border=True):
                render_contract(contract)
    else:
        st.info("No contract terms are loaded for the selected player.")

    st.subheader("Bonuses")
    bonus_count = 0
    for contract in contracts:
        for bonus in contract.get("bonuses", []):
            bonus_count += 1
            with st.container(border=True):
                render_bonus(contract.get("id"), bonus)
    if bonus_count == 0:
        st.info("No bonuses are loaded for the selected player.")


if __name__ == "__main__":
    main()
