import requests

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
TIMEOUT_SECONDS = 10


class StatsBombFetchError(Exception):
    """Raised when a StatsBomb open-data request does not return HTTP 200."""


def _get_json(url: str) -> list[dict]:
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise StatsBombFetchError(
            f"StatsBomb fetch failed: {url} ({response.status_code})"
        )
    return response.json()


def fetch_competitions() -> list[dict]:
    return _get_json(f"{BASE_URL}/competitions.json")


def fetch_matches(competition_id: int, season_id: int) -> list[dict]:
    return _get_json(f"{BASE_URL}/matches/{competition_id}/{season_id}.json")


def fetch_lineups(match_id: int) -> list[dict]:
    return _get_json(f"{BASE_URL}/lineups/{match_id}.json")


def fetch_events(match_id: int) -> list[dict]:
    return _get_json(f"{BASE_URL}/events/{match_id}.json")
