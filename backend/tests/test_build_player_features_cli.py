import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "features" / "build_player_features.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("build_player_features", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_player_features = _load_module()


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_main_commits_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(build_player_features, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        build_player_features, "build_season_features", lambda session, season_id: 3
    )

    build_player_features.main(["--season-id", "106"])

    captured = capsys.readouterr()
    assert "3" in captured.out
    assert "106" in captured.out
    assert fake_session.committed is True
