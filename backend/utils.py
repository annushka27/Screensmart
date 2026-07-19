import os
import json

# DB file at root ScreenSmart folder
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "candidates.json")

def load_candidates():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_candidates(candidates):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with open(DB_FILE, "w") as f:
        json.dump(candidates, f, indent=4)
