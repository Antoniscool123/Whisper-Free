import json
from pathlib import Path

import app


def settings(**overrides):
    base = dict(app.DEFAULT)
    base.update(overrides)
    return base


def test_polish_removes_fillers_and_duplicates():
    result = app.polish("øh hello hello world", settings())
    assert result == "Hello world"


def test_polish_supports_danish_and_english_line_commands():
    assert app.polish("første ny linje anden", settings()) == "Første \n anden"
    assert app.polish("first new paragraph second", settings()) == "First \n\n second"


def test_polish_can_preserve_raw_filler_words():
    result = app.polish("um test", settings(remove_fillers=False))
    assert result == "Um test"


def test_language_codes_include_danish_and_auto_detection():
    assert app.LANGS["Dansk"] == "da"
    assert app.LANGS["Auto detect"] is None


def test_json_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "DIR", tmp_path)
    target = tmp_path / "settings.json"
    value = {"language": "Dansk", "model": "small"}
    app.write_json(target, value)
    assert app.read_json(target, {}) == value


def test_invalid_json_returns_default(tmp_path):
    target = tmp_path / "broken.json"
    target.write_text("{broken", encoding="utf-8")
    assert app.read_json(target, {"safe": True}) == {"safe": True}
