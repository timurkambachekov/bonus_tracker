from datetime import date, datetime
from pathlib import Path
import sys

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.api_client import load_dataset, load_player_detail


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
    if isinstance(value, (datetime, date)):
        return value.strftime("%d.%m.%Y")
    try:
        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y")
    except ValueError:
        return str(value)


def format_condition(condition):
    names = {
        "games_played": "games",
        "starts": "starts",
        "full_games": "full games",
        "minutes_played": "minutes",
        "goals": "goals",
        "assists": "assists",
        "goal_contributions": "goal contributions",
        "yellow_cards": "yellow cards",
        "red_cards": "red cards",
    }
    directions = {
        ">=": "at least",
        ">": "more than",
        "=": "exactly",
        "<=": "at most",
        "<": "less than",
    }

    threshold = condition.get("threshold")
    threshold_text = threshold
    if threshold not in (None, ""):
        numeric = float(threshold)
        threshold_text = int(numeric) if numeric.is_integer() else numeric

    return (
        f"{directions.get(condition.get('direction'), condition.get('direction') or '')} "
        f"{threshold_text} "
        f"{names.get(condition.get('condition_type'), condition.get('condition_type') or 'condition')}"
    )


def format_bonus(bonus):
    bonus_type = (bonus.get("bonus_type") or "bonus").replace("_", " ").title()
    clause_key = bonus.get("clause_key")
    conditions = bonus.get("conditions") or []
    competition = bonus.get("competition_name") or bonus.get("competition_code") or "official"
    operator = f" {str(bonus.get('condition_operator') or 'and').upper()} "
    condition_text = operator.join(format_condition(condition) for condition in conditions)
    if not condition_text:
        condition_text = "defined conditions"

    label = bonus_type if not clause_key else f"{bonus_type} [{clause_key}]"
    return (
        f"{label}: {format_money(bonus.get('bonus_value') or 0)} RUB "
        f"for {condition_text} in {competition}."
    )


@st.cache_data(show_spinner=False)
def cached_dataset():
    return load_dataset()


@st.cache_data(show_spinner=False)
def cached_player_detail(player_id: int):
    return load_player_detail(player_id)


def main():
    st.set_page_config(page_title="bonus_tracker", layout="wide")
    st.title("Player Bonus Tracker")

    try:
        clubs, players = cached_dataset()
    except requests.RequestException as exc:
        st.error(f"Could not load backend data: {exc}")
        return

    club_options = [""] + [club["club_slug"] for club in clubs]
    club_names = {
        club["club_slug"]: club.get("club_name") or club["club_slug"] for club in clubs
    }
    selected_club = st.selectbox(
        "Club",
        club_options,
        format_func=lambda slug: "Choose a club" if not slug else club_names.get(slug, slug),
    )
    if not selected_club:
        return

    club_players = [player for player in players if player.get("club_slug") == selected_club]
    player_options = [""] + [player["id"] for player in club_players]
    player_names = {
        player["id"]: player.get("player_name") or "Unknown player" for player in club_players
    }
    selected_player_id = st.selectbox(
        "Player",
        player_options,
        format_func=lambda player_id: "Choose a player" if not player_id else player_names[player_id],
    )
    if not selected_player_id:
        return

    try:
        payload = cached_player_detail(selected_player_id)
        print(payload)
    except requests.RequestException as exc:
        st.error(f"Could not load player detail: {exc}")
        return

    player = payload["player"]
    stats_rows = payload.get("stats") or []
    contracts = payload.get("contracts") or []
    totals = payload.get("totals") or {}

    st.subheader(player.get("player_name") or "Player")
    cols = st.columns(4)
    fields = [
        ("Club", player.get("club_name") or player.get("club_slug") or "-"),
        ("Position", player.get("position") or "-"),
        ("Nationality", player.get("nationality") or "-"),
        ("Date of Birth", format_date(player.get("date_of_birth"))),
        ("Height (m)", player.get("height_m") or "-"),
        ("Foot", player.get("foot") or "-"),
        ("Market Value EUR", format_money(player.get("market_value_eur"))),
        ("Total Bonus Payout", format_money(totals.get("total_payout_value") or 0)),
    ]
    for index, (label, value) in enumerate(fields):
        cols[index % 4].metric(label, value)

    st.subheader("Season Stats")
    if stats_rows:
        formatted_stats = []
        for row in stats_rows:
            item = dict(row)
            if item.get("ppg") is not None:
                item["ppg"] = f"{float(item['ppg']):.2f}"
            formatted_stats.append(item)
        st.dataframe(formatted_stats, use_container_width=True, hide_index=True)
    else:
        st.info("No season stats are loaded for the selected player.")

    st.subheader("Contracts")
    if not contracts:
        st.info("No contract terms are loaded for the selected player.")
    for contract in contracts:
        with st.container(border=True):
            st.write(f"**Club:** {contract.get('club_name') or contract.get('club_slug') or '-'}")
            st.write(f"**Base salary:** {format_money(contract.get('base_salary'))} RUB/month")
            st.write(
                f"**Term:** {format_date(contract.get('contract_start'))} — {format_date(contract.get('contract_end'))}"
            )
            if contract.get("contract_text"):
                st.write(contract["contract_text"])
            st.write(
                f"**Total payout from bonuses:** {format_money(contract.get('total_payout_value') or 0)} RUB"
            )

            bonuses = contract.get("bonuses") or []
            if bonuses:
                st.write("**Bonuses**")
            for bonus in bonuses:
                st.write(format_bonus(bonus))
                progress = bonus.get("progress")
                if progress:
                    ratio = progress.get("completion_ratio")
                    ratio_text = f"{int(ratio * 100)}%" if ratio is not None else "n/a"
                    status = "achieved" if progress.get("achieved") else "in progress"
                    st.caption(
                        f"Season {progress.get('season') or '-'} | "
                        f"Progress: {ratio_text} | "
                        f"Status: {status} | "
                        f"Payout: {format_money(bonus.get('payout_value') or 0)} RUB"
                    )


if __name__ == "__main__":
    main()
