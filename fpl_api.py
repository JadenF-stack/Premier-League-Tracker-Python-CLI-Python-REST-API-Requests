import requests

API_KEY = "32e41bd3360648de82bca60c5e30f9ca"
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}


class FootballDataError(Exception):
    """Raised when the API call fails or returns invalid data."""


def _get(endpoint, params=None):
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
        # Valid response but bad status code (e.g. 401, 403, 429, 500)
        code = getattr(resp, "status_code", None)
        raise FootballDataError(f"API request failed (HTTP {code}).") from e

    except requests.exceptions.RequestException as e:
        # Network-related errors like timeouts, connection issues, DNS problems
        raise FootballDataError("Network error calling the football API.") from e

    except ValueError as e:
        # Response isn't valid JSON
        raise FootballDataError("API returned invalid JSON.") from e


def get_standings():
    """Premier League table. Calls _get() with the correct endpoint."""
    return _get("/competitions/PL/standings")


def get_matches(status=None, limit=None):
    """
    Premier League matches.
    Status examples: SCHEDULED, FINISHED, IN_PLAY
    """
    params = {}
    if status:
        params["status"] = status
    if limit:
        params["limit"] = limit
    return _get("/competitions/PL/matches", params=params or None)


def get_scorers(limit=10):
    """
    Get the Premier League top scorers.
    limit controls how many players are returned.
    """
    return _get("/competitions/PL/scorers", params={"limit": limit})


