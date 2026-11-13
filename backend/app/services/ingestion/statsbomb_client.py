import requests

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
TIMEOUT_SECONDS = 10


class StatsBombFetchError(Exception):
    """Raised when a StatsBomb open-data request fails: a network error
    (connection failure, timeout, ...), a non-200 HTTP status, or a
    response body that is not valid JSON."""


def _get_json(url: str) -> list[dict]:
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as exc:
        raise StatsBombFetchError(f"StatsBomb fetch failed: {url} ({exc})") from exc
    if response.status_code != 200:
        raise StatsBombFetchError(
            f"StatsBomb fetch failed: {url} ({response.status_code})"
        )
    try:
        return response.json()
    except ValueError as exc:
        # Covers json.JSONDecodeError and requests' own JSONDecodeError,
        # both ValueError subclasses.
        raise StatsBombFetchError(
            f"StatsBomb fetch returned invalid JSON: {url} ({exc})"
        ) from exc


def fetch_competitions() -> list[dict]:
    return _get_json(f"{BASE_URL}/competitions.json")


def fetch_matches(competition_id: int, season_id: int) -> list[dict]:
    return _get_json(f"{BASE_URL}/matches/{competition_id}/{season_id}.json")


def fetch_lineups(match_id: int) -> list[dict]:
    return _get_json(f"{BASE_URL}/lineups/{match_id}.json")


def fetch_events(match_id: int) -> list[dict]:
    return _get_json(f"{BASE_URL}/events/{match_id}.json")
