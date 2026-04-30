import json
import os
import subprocess
import sys
import time

import requests


def create_profile():
    url = "http://localhost:8000/api/user/profile"
    payload = {
        "user_id": "game_user",  # ID personalizado
        "name": "Ainz",  # Nombre display
        "preferred_tone": "casual",
        "theme": "dark",
    }

    print(f"Connecting to {url}...")
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("[SUCCESS] User profile created!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"[ERROR] Failed to create profile: {response.text}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to Web API.")
        print("Make sure 'launch_conversational.bat' is running!")


if __name__ == "__main__":
    create_profile()
