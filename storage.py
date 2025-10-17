import json
from pathlib import Path

# automatically find the correct users file
USERS_PATH_CANDIDATES = [Path("data/users.json"), Path("users.JSON")]
for _p in USERS_PATH_CANDIDATES:
    USERS_PATH = _p
    if _p.exists():
        break
USERS_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_users() -> dict:
    if USERS_PATH.exists():
        with USERS_PATH.open("r") as f:
            return json.load(f)
    return {}

def save_users(users: dict) -> None:
    with USERS_PATH.open("w") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)