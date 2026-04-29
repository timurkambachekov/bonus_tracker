from fastapi import APIRouter, HTTPException

from app.backend.repositories.users import (
    fetch_active_app_user_by_email,
    list_user_clubs,
    touch_app_user_login,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"], 
)


def build_app_user_response(email: str):
    app_user = fetch_active_app_user_by_email(email)
    if not app_user:
        return None

    clubs = list_user_clubs(app_user["id"])
    return {
        "id": app_user["id"],
        "email": app_user["email"],
        "full_name": app_user["full_name"],
        "role": app_user["role"],
        "club_ids": [club["id"] for club in clubs],
        "competition_ids": sorted(
            {club["competition_id"] for club in clubs if club["competition_id"]}
        ),
        "is_admin": app_user["role"] == "admin",
    }


@router.get("/by-email")
def app_user_by_email(email: str):
    app_user = build_app_user_response(email)
    if not app_user:
        raise HTTPException(status_code=404, detail="App user not found")
    return app_user


@router.post("/{user_id}/touch-login")
def touch_app_user(user_id: int):
    touch_app_user_login(user_id)
    return {"ok": True}
