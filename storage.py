import json
from pathlib import Path

# Always point to the same file:
USERS_PATH = Path(__file__).resolve().parent / "data" / "users.json"
USERS_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_users() -> dict:
    if USERS_PATH.exists():
        with USERS_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users: dict) -> None:
    with USERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
