from app.backend.db import get_connection


def fetch_active_app_user_by_email(email: str):
    normalized_email = email.strip().lower()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    email,
                    full_name,
                    role,
                    is_active,
                    last_login_at,
                    created_at
                FROM app_users
                WHERE LOWER(email) = %s
                  AND is_active = TRUE
                LIMIT 1;
                """,
                (normalized_email,),
            )
            return cursor.fetchone()


def upsert_app_user(
    email: str,
    full_name=None,
    role: str = "club_rep",
    is_active: bool = True,
):
    normalized_email = email.strip().lower()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_users (
                    email,
                    full_name,
                    role,
                    is_active
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                SET
                    full_name = EXCLUDED.full_name,
                    role = EXCLUDED.role,
                    is_active = EXCLUDED.is_active
                RETURNING
                    id,
                    email,
                    full_name,
                    role,
                    is_active,
                    last_login_at,
                    created_at;
                """,
                (normalized_email, full_name, role, is_active),
            )
            return cursor.fetchone()


def replace_user_clubs(user_id: int, club_ids):
    unique_club_ids = sorted(set(club_ids))
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM app_user_clubs
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            for club_id in unique_club_ids:
                cursor.execute(
                    """
                    INSERT INTO app_user_clubs (
                        user_id,
                        club_id
                    )
                    VALUES (%s, %s);
                    """,
                    (user_id, club_id),
                )
        connection.commit()


def list_user_clubs(user_id: int):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    clubs.id,
                    clubs.club_name,
                    clubs.club_slug,
                    clubs.competition_id
                FROM app_user_clubs
                JOIN clubs ON clubs.id = app_user_clubs.club_id
                WHERE app_user_clubs.user_id = %s
                ORDER BY clubs.club_name, clubs.id;
                """,
                (user_id,),
            )
            return cursor.fetchall()


def touch_app_user_login(user_id: int):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE app_users
                SET last_login_at = NOW()
                WHERE id = %s;
                """,
                (user_id,),
            )
        connection.commit()
