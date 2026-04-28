from typing import TYPE_CHECKING, Any, Optional

from app.db import get_connection

if TYPE_CHECKING:
    from psycopg.abc import Params, Query
else:
    Params = Any
    Query = Any


def fetch_rows(query: Query, params: Optional[Params] = None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def fetch_one(query: Query, params: Optional[Params] = None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()


def ping_database():
    return fetch_one("SELECT 1 AS ok;")


def get_summary():
    return fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM clubs) AS clubs,
            (SELECT COUNT(*) FROM players) AS players,
            (SELECT COUNT(*) FROM player_season_stats) AS stats,
            (SELECT COUNT(*) FROM contracts) AS contracts,
            (SELECT COUNT(*) FROM contract_bonuses) AS bonuses;
        """
    )


def list_clubs():
    return fetch_rows(
        """
        SELECT
            c.id,
            c.transfermarkt_club_id,
            c.club_slug,
            c.club_name,
            COUNT(p.id) AS player_count
        FROM clubs c
        LEFT JOIN players p ON p.club_id = c.id
        GROUP BY c.id, c.transfermarkt_club_id, c.club_slug, c.club_name
        ORDER BY COALESCE(c.club_name, c.club_slug);
        """
    )


def list_players(limit: int):
    return fetch_rows(
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
            comp.id AS competition_id,
            comp.transfermarkt_code AS competition_code,
            comp.name AS competition_name,
            comp.country AS competition_country,
            comp.season AS competition_season
        FROM players p
        LEFT JOIN clubs c ON c.id = p.club_id
        LEFT JOIN competitions comp ON comp.id = c.competition_id
        ORDER BY p.player_name
        LIMIT %s;
        """,
        (limit,),
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
            comp.id AS competition_id,
            comp.transfermarkt_code AS competition_code,
            comp.name AS competition_name,
            comp.country AS competition_country,
            comp.season AS competition_season
        FROM players p
        LEFT JOIN clubs c ON c.id = p.club_id
        LEFT JOIN competitions comp ON comp.id = c.competition_id
        WHERE p.id = %s;
        """,
        (player_id,),
    )


def fetch_player_stats(player_id: int):
    return fetch_rows(
        """
        SELECT
            season,
            squad_inclusions,
            appearances,
            starts,
            full_games,
            goals,
            assists,
            yellow_cards,
            red_cards,
            substitutions_on,
            substitutions_off,
            minutes_played,
            ppg
        FROM player_season_stats
        WHERE player_id = %s
        ORDER BY season DESC, id DESC;
        """,
        (player_id,),
    )


def fetch_contracts_for_player(player_id: int):
    return fetch_rows(
        """
        SELECT
            ct.id,
            ct.player_id,
            ct.club_id,
            ct.base_salary,
            ct.contract_start,
            ct.contract_end,
            ct.contract_text,
            c.club_slug,
            c.club_name
        FROM contracts ct
        LEFT JOIN clubs c ON c.id = ct.club_id
        WHERE ct.player_id = %s
        ORDER BY ct.contract_start DESC NULLS LAST, ct.id DESC;
        """,
        (player_id,),
    )


def fetch_contract_bonuses(player_id: Optional[int] = None):
    query = """
        SELECT
            cb.id,
            cb.contract_id,
            cb.clause_key,
            cb.bonus_type,
            cb.condition_operator,
            cb.bonus_value,
            cb.display_order,
            comp.id AS competition_id,
            comp.transfermarkt_code AS competition_code,
            comp.name AS competition_name,
            cbg.group_name AS binding_group
        FROM contract_bonuses cb
        JOIN competitions comp ON comp.id = cb.competition_id
        LEFT JOIN contract_bonus_binding_group_members cbgm
            ON cbgm.contract_bonus_id = cb.id
        LEFT JOIN contract_bonus_binding_groups cbg
            ON cbg.id = cbgm.binding_group_id
    """

    if player_id is None:
        return fetch_rows(
            query
            + """
            ORDER BY cb.contract_id, cb.display_order, cb.id;
            """
        )

    return fetch_rows(
        query
        + """
        WHERE cb.contract_id IN (
            SELECT id FROM contracts WHERE player_id = %s
        )
        ORDER BY cb.contract_id, cb.display_order, cb.id;
        """,
        (player_id,),
    )


def fetch_contract_bonus_conditions(player_id: Optional[int] = None):
    query = """
        SELECT
            cbc.id,
            cbc.contract_bonus_id,
            cbc.condition_type,
            cbc.direction,
            cbc.threshold,
            cbc.display_order
        FROM contract_bonus_conditions cbc
        JOIN contract_bonuses cb ON cb.id = cbc.contract_bonus_id
    """

    if player_id is None:
        return fetch_rows(
            query
            + """
            ORDER BY cbc.contract_bonus_id, cbc.display_order, cbc.id;
            """
        )

    return fetch_rows(
        query
        + """
        WHERE cb.contract_id IN (
            SELECT id FROM contracts WHERE player_id = %s
        )
        ORDER BY cbc.contract_bonus_id, cbc.display_order, cbc.id;
        """,
        (player_id,),
    )


def list_stats(limit: int):
    return fetch_rows(
        """
        SELECT
            s.id,
            p.player_name,
            c.club_slug,
            c.club_name,
            s.season,
            s.squad_inclusions,
            s.appearances,
            s.starts,
            s.full_games,
            s.goals,
            s.assists,
            s.minutes_played,
            s.ppg
        FROM player_season_stats s
        LEFT JOIN players p ON p.id = s.player_id
        LEFT JOIN clubs c ON c.id = s.club_id
        ORDER BY c.club_slug, p.player_name
        LIMIT %s;
        """,
        (limit,),
    )


def list_spartak_contracts():
    return fetch_rows(
        """
        SELECT
            ct.id,
            ct.player_id,
            ct.club_id,
            p.player_name,
            ct.base_salary,
            ct.contract_start,
            ct.contract_end
        FROM contracts ct
        JOIN players p ON p.id = ct.player_id
        JOIN clubs c ON c.id = ct.club_id
        WHERE c.club_slug = 'spartak-moscou'
        ORDER BY p.player_name;
        """
    )
