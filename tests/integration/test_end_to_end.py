from app.brain.orchestrator import VictorCore
from app.config import load_config
from app.tools.factory import build_registry


def _core(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = load_config("config/default.yaml")
    config.filesystem.allowed_roots = [str(tmp_path)]
    registry = build_registry(config)
    return VictorCore(config, registry)


def test_end_to_end_list_directory(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hi")
    core = _core(tmp_path, monkeypatch)

    reply = core.handle_input(f"list files in {tmp_path}")

    assert "notes.txt" in reply
    assert "Sir" in reply


def test_end_to_end_small_talk_does_not_touch_filesystem(tmp_path, monkeypatch):
    core = _core(tmp_path, monkeypatch)
    reply = core.handle_input("who are you?")
    assert "Victor" in reply


def test_end_to_end_unknown_path_reports_friendly_error(tmp_path, monkeypatch):
    core = _core(tmp_path, monkeypatch)
    reply = core.handle_input(f"list files in {tmp_path / 'missing'}")
    assert "Sir" in reply or "does not exist" in reply