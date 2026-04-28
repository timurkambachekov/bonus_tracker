import os

import requests

API_BASE_URL = os.getenv("BONUS_TRACKER_API_URL", "http://127.0.0.1:8000")


def fetch_json(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def load_dataset():
    clubs = fetch_json("/api/clubs")["items"]
    players = fetch_json("/api/players?limit=2000")["items"]
    return clubs, players


def load_player_detail(player_id: int):
    return fetch_json(f"/api/players/{player_id}")
