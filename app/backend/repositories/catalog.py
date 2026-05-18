from typing import List, Optional

from app.backend.db import get_connection


def fetch_rows(query: str, params=()):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def fetch_one(query: str, params=()):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()


def list_competitions(season: Optional[int] = None):
    if season is None:
        return fetch_rows(
            """
            SELECT
                id,
                transfermarkt_code,
                name,
                country,
                season
            FROM competitions
            ORDER BY country, name, season DESC, id DESC;
            """
        )

    return fetch_rows(
        """
        SELECT
            id,
            transfermarkt_code,
            name,
            country,
            season
        FROM competitions
        WHERE season = %s
        ORDER BY country, name, season DESC, id DESC;
        """,
        (season,),
    )


def list_clubs_by_competition(competition_id: int, season: Optional[int] = None):
    params = [competition_id]
    where_clauses = ["club_competitions.competition_id = %s"]

    if season is not None:
        where_clauses.append("club_competitions.season = %s")
        params.append(season)

    return fetch_rows(
        f"""
        SELECT
            clubs.id,
            clubs.transfermarkt_club_id,
            clubs.club_slug,
            clubs.club_name,
            club_competitions.competition_id,
            club_competitions.season
        FROM clubs
        JOIN club_competitions ON club_competitions.club_id = clubs.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY club_competitions.season DESC, clubs.club_name, clubs.id;
        """,
        tuple(params),
    )


def list_players_by_competition(competition_id: int, season: Optional[int] = None):
    params = [competition_id]
    where_clauses = ["club_competitions.competition_id = %s"]

    if season is not None:
        where_clauses.append("player_clubs.season = %s")
        params.append(season)

    return fetch_rows(
        f"""
        SELECT
            p.id,
            p.transfermarkt_player_id,
            p.player_name,
            p.position,
            p.nationality,
            p.height_m,
            p.foot,
            p.market_value_eur,
            c.id AS club_id,
            c.club_slug,
            c.club_name,
            club_competitions.competition_id,
            player_clubs.season
        FROM players p
        JOIN player_clubs ON player_clubs.player_id = p.id
        JOIN clubs c ON c.id = player_clubs.club_id
        JOIN club_competitions
            ON club_competitions.club_id = player_clubs.club_id
           AND club_competitions.season = player_clubs.season
        WHERE {' AND '.join(where_clauses)}
        ORDER BY player_clubs.season DESC, c.club_name, p.player_name, p.id;
        """,
        tuple(params),
    )


def list_players_by_club(club_id: int, season: Optional[int] = None):
    params = [club_id]
    where_clauses = ["player_clubs.club_id = %s"]

    if season is not None:
        where_clauses.append("player_clubs.season = %s")
        params.append(season)

    return fetch_rows(
        f"""
        SELECT
            p.id,
            p.transfermarkt_player_id,
            p.player_name,
            p.position,
            p.nationality,
            p.height_m,
            p.foot,
            p.market_value_eur,
            c.id AS club_id,
            c.transfermarkt_club_id,
            c.club_slug,
            c.club_name,
            club_competitions.competition_id,
            player_clubs.season
        FROM players p
        JOIN player_clubs ON player_clubs.player_id = p.id
        JOIN clubs c ON c.id = player_clubs.club_id
        LEFT JOIN LATERAL (
            SELECT competition_id, season
            FROM club_competitions
            WHERE club_id = c.id
              AND season = player_clubs.season
            LIMIT 1
        ) club_competitions ON TRUE
        WHERE {' AND '.join(where_clauses)}
        ORDER BY player_clubs.season DESC, p.player_name, p.id;
        """,
        tuple(params),
    )


def fetch_player_by_id(player_id: int):
    return fetch_one(
        """
        SELECT
            p.id,
            p.transfermarkt_player_id,
            p.player_name,
            p.position,
            p.date_of_birth,
            p.nationality,
            p.height_m,
            p.foot,
            p.market_value_eur,
            c.id AS club_id,
            c.transfermarkt_club_id,
            c.club_slug,
            c.club_name,
            competition.id AS competition_id,
            competition.transfermarkt_code,
            competition.name AS competition_name,
            competition.country AS competition_country,
            player_clubs.season AS competition_season
        FROM players p
        JOIN LATERAL (
            SELECT club_id, season
            FROM player_clubs
            WHERE player_id = p.id
            ORDER BY season DESC, club_id DESC
            LIMIT 1
        ) player_clubs ON TRUE
        JOIN clubs c ON c.id = player_clubs.club_id
        LEFT JOIN LATERAL (
            SELECT competition_id, season
            FROM club_competitions
            WHERE club_id = c.id
              AND season = player_clubs.season
            LIMIT 1
        ) club_competitions ON TRUE
        LEFT JOIN competitions competition ON competition.id = club_competitions.competition_id
        WHERE p.id = %s;
        """,
        (player_id,),
    )


def fetch_active_contract_by_player(player_id: int):
    return fetch_one(
        """
        SELECT
            contracts.id,
            contracts.player_id,
            contracts.club_id,
            contracts.base_salary,
            contracts.contract_start,
            contracts.contract_end,
            contracts.contract_text,
            contracts.created_at
        FROM contracts
        WHERE contracts.player_id = %s
          AND contracts.contract_start <= CURRENT_DATE
          AND contracts.contract_end >= CURRENT_DATE
        ORDER BY contracts.contract_start DESC, contracts.contract_end DESC, contracts.id DESC
        LIMIT 1;
        """,
        (player_id,),
    )


def fetch_stats_by_player(
    player_id: int,
    seasons: Optional[List[int]] = None,
    club_id: Optional[int] = None,
    competition_id: Optional[int] = None,
):
    params = [player_id]
    where_clauses = ["player_id = %s"]

    if seasons:
        where_clauses.append("season = ANY(%s)")
        params.append(seasons)

    if club_id is not None:
        where_clauses.append("club_id = %s")
        params.append(club_id)

    if competition_id is not None:
        where_clauses.append("competition_id = %s")
        params.append(competition_id)

    return fetch_rows(
        f"""
        SELECT
            id,
            player_id,
            club_id,
            competition_id,
            season,
            squad_inclusions,
            appearances,
            starts,
            full_games,
            substitutions_on,
            substitutions_off,
            minutes_played,
            goals,
            assists,
            yellow_cards,
            second_yellow_cards,
            red_cards,
            ppg,
            created_at
        FROM player_season_stats
        WHERE {' AND '.join(where_clauses)}
        ORDER BY season DESC, competition_id DESC NULLS LAST, created_at DESC, id DESC;
        """,
        tuple(params),
    )


def list_bonuses_by_contract(contract_id: int):
    return fetch_rows(
        """
        SELECT
            contract_bonuses.id,
            contract_bonuses.contract_id,
            contract_bonuses.bonus_type,
            contract_bonuses.competition_id,
            competitions.transfermarkt_code AS competition_code,
            competitions.name AS competition_name,
            contract_bonus_binding_groups.group_name AS binding_group,
            contract_bonuses.condition_operator,
            contract_bonuses.bonus_value,
            contract_bonuses.display_order,
            contract_bonuses.created_at
        FROM contract_bonuses
        LEFT JOIN competitions ON competitions.id = contract_bonuses.competition_id
        LEFT JOIN contract_bonus_binding_group_members
            ON contract_bonus_binding_group_members.contract_bonus_id = contract_bonuses.id
        LEFT JOIN contract_bonus_binding_groups
            ON contract_bonus_binding_groups.id = contract_bonus_binding_group_members.binding_group_id
        WHERE contract_bonuses.contract_id = %s
        ORDER BY contract_bonuses.display_order NULLS LAST, contract_bonuses.id;
        """,
        (contract_id,),
    )


def list_conditions_by_bonus(contract_bonus_id: int):
    return fetch_rows(
        """
        SELECT
            contract_bonus_conditions.id,
            contract_bonus_conditions.contract_bonus_id,
            contract_bonus_conditions.condition_type,
            contract_bonus_conditions.direction,
            contract_bonus_conditions.threshold,
            contract_bonus_conditions.display_order,
            contract_bonus_conditions.created_at
        FROM contract_bonus_conditions
        WHERE contract_bonus_conditions.contract_bonus_id = %s
        ORDER BY contract_bonus_conditions.display_order NULLS LAST, contract_bonus_conditions.id;
        """,
        (contract_bonus_id,),
    )
