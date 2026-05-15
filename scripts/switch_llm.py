#!/usr/bin/env python3
"""
Interactive CLI script to switch LLM provider on Render.

Required environment variables (auto-loaded from .env if present):
  RENDER_API_KEY    - Your Render API key (generate at dashboard.render.com)
  RENDER_SERVICE_ID - Your Render service ID (found in service URL)

Usage:
  python scripts/switch_llm.py
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

RENDER_API_BASE = "https://api.render.com/v1"


def load_dotenv():
    """Load environment variables from .env file if it exists."""
    # Look for .env in project root (one level up from scripts/)
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Only set if not already in environment (explicit exports take precedence)
            if key not in os.environ:
                os.environ[key] = value
ENV_VAR_NAME = "LLM_PROVIDER"

AVAILABLE_PROVIDERS = {
    "1": {"name": "gemini", "description": "Google Gemini 2.5 Flash"},
    "2": {"name": "deepseek", "description": "DeepSeek V4 Chat"},
}


def get_env_or_exit(var_name: str) -> str:
    value = os.environ.get(var_name)
    if not value:
        print(f"Error: {var_name} environment variable is required.")
        print(f"Export it with: export {var_name}=your_value")
        sys.exit(1)
    return value


def render_api_request(method: str, endpoint: str, api_key: str, data: dict = None) -> dict:
    url = f"{RENDER_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    request_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                return {}
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"API Error ({e.code}): {error_body}")
        sys.exit(1)


def get_current_provider(api_key: str, service_id: str) -> str | None:
    """Fetch current LLM_PROVIDER value from Render."""
    try:
        result = render_api_request(
            "GET",
            f"/services/{service_id}/env-vars/{ENV_VAR_NAME}",
            api_key
        )
        return result.get("envVar", {}).get("value")
    except SystemExit:
        return None


def set_provider(api_key: str, service_id: str, provider: str) -> bool:
    """Update LLM_PROVIDER on Render."""
    render_api_request(
        "PUT",
        f"/services/{service_id}/env-vars/{ENV_VAR_NAME}",
        api_key,
        {"value": provider}
    )
    return True


def print_menu(current_provider: str | None):
    print("\n" + "=" * 50)
    print("  LLM Provider Switcher for Render")
    print("=" * 50)

    if current_provider:
        print(f"\n  Current provider: {current_provider}")
    else:
        print(f"\n  Current provider: not set (will default to 'gemini')")

    print("\n  Available providers:\n")
    for key, provider in AVAILABLE_PROVIDERS.items():
        marker = " <-- current" if provider["name"] == current_provider else ""
        print(f"    [{key}] {provider['name']:12} - {provider['description']}{marker}")

    print(f"\n    [q] Quit without changes")
    print()


def main():
    load_dotenv()
    api_key = get_env_or_exit("RENDER_API_KEY")
    service_id = get_env_or_exit("RENDER_SERVICE_ID")

    current_provider = get_current_provider(api_key, service_id)
    print_menu(current_provider)

    while True:
        choice = input("  Select provider [1/2/q]: ").strip().lower()

        if choice == "q":
            print("\n  No changes made. Goodbye!\n")
            sys.exit(0)

        if choice not in AVAILABLE_PROVIDERS:
            print("  Invalid choice. Please enter 1, 2, or q.")
            continue

        selected = AVAILABLE_PROVIDERS[choice]

        if selected["name"] == current_provider:
            print(f"\n  '{selected['name']}' is already the current provider.")
            continue

        # Confirm the switch
        confirm = input(
            f"\n  Switch from '{current_provider or 'gemini'}' to '{selected['name']}'? [y/N]: "
        ).strip().lower()

        if confirm != "y":
            print("  Cancelled.")
            continue

        print(f"\n  Updating LLM_PROVIDER to '{selected['name']}'...")
        set_provider(api_key, service_id, selected["name"])
        print(f"  Done! LLM_PROVIDER is now set to '{selected['name']}'.")
        print("\n  Note: Render will redeploy your service automatically.\n")
        break


if __name__ == "__main__":
    main()
