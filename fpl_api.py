from __future__ import annotations

from typing import Any, Dict, Optional

import requests

API_KEY = ""

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}


class FootballDataError(Exception):
    """Raised when the API call fails or returns invalid data."""


def _get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generic GET request wrapper:
    - Adds required auth header
    - Handles HTTP errors cleanly
    - Returns JSON dict
    """
    try:
        # Make the request to the API
        resp = requests.get(
            f"{BASE_URL}{endpoint}", # join the base url with the endpoint
            headers=HEADERS, # include API key
            params=params, # query string parameters
            timeout=20, # prevents the program hanging forever
        )
        resp.raise_for_status()
        return resp.json()
    
    except requests.exceptions.HTTPError as e:
        # This catches "valid response, but bad status code" errors (e.g. 401, 403, 429, 500)
        code = getattr(resp, "status_code", None)
        raise FootballDataError(f"API request failed (HTTP {code}).") from e
    
    except requests.exceptions.RequestException as e:
        # This catches network-related errors like timeouts, connection issues, DNS problems, etc.
        raise FootballDataError("Network error calling the football API.") from e
    
    except ValueError as e:
        # This catches cases where the response isn't valid JSON for some reason
        raise FootballDataError("API returned invalid JSON.") from e


def get_standings() -> Dict[str, Any]:
    """Premier League table. This just calls _get() with the correct endpoint.
    Keeping this as a separate function makes main.py cleaner."""
    return _get("/competitions/PL/standings")


def get_matches(status: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Premier League matches status examples: SCHEDULED, FINISHED, IN_PLAY
    """
    params: Dict[str, Any] = {}
    if status:
        params["status"] = status
    if limit:
        params["limit"] = limit
    return _get("/competitions/PL/matches", params=params or None)


def get_scorers(limit: int = 10) -> Dict[str, Any]:
    """
    Get the Premier League top scorers list.

    The API supports a scorers endpoint for the PL competition.
    I pass limit so I can control how many players are returned.
    """
    return _get("/competitions/PL/scorers", params={"limit": limit})



