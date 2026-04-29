import streamlit as st

from app.backend.services import calculate_bonus_progress
from app.frontend.api_client import load_clubs, load_competitions, load_players
from app.frontend.charts import group_conditions_by_type, render_condition_number_line
from app.frontend.formatters import build_stats_row, format_bonus_title, format_money


def render_filters(app_user):
    if not app_user["is_admin"] and len(app_user["club_ids"]) == 1:
        club_players = load_players(app_user["club_ids"][0])
        if not club_players:
            st.info("No players available for your club.")
            return None
        return st.selectbox(
            "Player",
            [None] + club_players,
            format_func=lambda item: "Choose a player" if item is None else item.name,
        )

    competitions = load_competitions()
    if not app_user["is_admin"]:
        competitions = [
            competition
            for competition in competitions
            if competition.id in app_user["competition_ids"]
        ]
    if not competitions:
        st.info("No authorized competitions.")
        return None

    selected_competition = st.selectbox(
        "League",
        [None] + competitions,
        format_func=lambda item: "Choose a competition" if item is None else item.name,
    )
    if not selected_competition:
        return None

    clubs = load_clubs(selected_competition.id)
    if not app_user["is_admin"]:
        clubs = [club for club in clubs if club.id in app_user["club_ids"]]
    if not clubs:
        st.info("No authorized clubs in this competition.")
        return None

    selected_club = st.selectbox(
        "Club",
        [None] + clubs,
        format_func=lambda item: "Choose a club" if item is None else item.name,
    )
    if not selected_club:
        return None

    club_players = load_players(selected_club.id)
    return st.selectbox(
        "Player",
        [None] + club_players,
        format_func=lambda item: "Choose a player" if item is None else item.name,
    )


def render_player_details(player):
    st.subheader(player.name)
    with st.container(border=True):
        detail_cols = st.columns(3)
        detail_items = [
            ("Position", player.position or "-"),
            ("Nationality", player.nationality or "-"),
            ("Date of Birth", player.date_of_birth or "-"),
            ("Height (m)", player.height_m or "-"),
            ("Foot", player.foot or "-"),
            ("Market Value", format_money(player.market_value_eur) or "-"),
        ]
        for index, (label, value) in enumerate(detail_items):
            with detail_cols[index % 3]:
                st.metric(label, value)


def render_seasonal_stats(stats):
    st.subheader("Seasonal Stats")
    if stats:
        st.dataframe([build_stats_row(stats)], hide_index=True, use_container_width=True)
        return
    st.write("No seasonal stats")


def render_contract(contract):
    st.subheader("Contract")
    if not contract:
        st.write("No active contract")
        return

    with st.container(border=True):
        contract_cols = st.columns(3)
        contract_items = [
            ("Start", contract.start_date),
            ("End", contract.end_date),
            ("Base Salary", format_money(contract.base_salary)),
        ]
        for index, (label, value) in enumerate(contract_items):
            with contract_cols[index]:
                st.metric(label, value)

        if contract.contract_text:
            st.write(contract.contract_text)


def render_bonus_card(index, bonus, stats):
    progress = calculate_bonus_progress(bonus, stats) if stats else None
    with st.container(border=True):
        st.markdown(f"**{format_bonus_title(index, bonus)}**")
        header_cols = st.columns(3)
        with header_cols[0]:
            st.metric("Payout", format_money(bonus.payout))
        with header_cols[1]:
            st.metric("Competition", bonus.competition_name or bonus.competition.value)
        with header_cols[2]:
            if progress:
                st.metric("Current Payout", format_money(progress["payout_value"]))
            else:
                st.metric("Current Payout", "-")

        st.write("Conditions")
        if not bonus.conditions:
            st.write("- None")
            return

        grouped_conditions = group_conditions_by_type(bonus.conditions)
        for condition_type, grouped in grouped_conditions.items():
            actual = progress["actuals"].get(condition_type) if progress else None
            render_condition_number_line(
                condition_type,
                grouped,
                actual,
                bonus.operator.value,
            )


def render_bonuses(bonuses, stats):
    st.subheader("Bonuses")
    if not bonuses:
        st.write("No bonuses")
        return

    for index, bonus in enumerate(bonuses, start=1):
        render_bonus_card(index, bonus, stats)
