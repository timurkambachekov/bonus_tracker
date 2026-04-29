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


def list_competitions():
    return fetch_rows(
        """
        SELECT
            id,
            transfermarkt_code,
            name,
            country,
            season
        FROM competitions
        ORDER BY country, name, season DESC, id;
        """
    )


def list_clubs_by_competition(competition_id: int):
    return fetch_rows(
        """
        SELECT
            id,
            transfermarkt_club_id,
            club_slug,
            club_name,
            competition_id
        FROM clubs
        WHERE competition_id = %s
        ORDER BY club_name, id;
        """,
        (competition_id,),
    )


def list_players_by_competition(competition_id: int):
    return fetch_rows(
        """
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
            c.competition_id
        FROM players p
        JOIN clubs c ON c.id = p.club_id
        WHERE c.competition_id = %s
        ORDER BY c.club_name, p.player_name, p.id;
        """,
        (competition_id,),
    )


def list_players_by_club(club_id: int):
    return fetch_rows(
        """
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
            c.competition_id
        FROM players p
        JOIN clubs c ON c.id = p.club_id
        WHERE c.id = %s
        ORDER BY p.player_name, p.id;
        """,
        (club_id,),
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
            competition.season AS competition_season
        FROM players p
        JOIN clubs c ON c.id = p.club_id
        JOIN competitions competition ON competition.id = c.competition_id
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


def fetch_latest_stats_by_player(player_id: int):
    return fetch_one(
        """
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
        WHERE player_id = %s
        ORDER BY season DESC, created_at DESC, id DESC
        LIMIT 1;
        """,
        (player_id,),
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
