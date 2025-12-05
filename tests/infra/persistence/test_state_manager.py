import json

from novelkit.infra.persistence.state import StateManager


def test_load_nonexistent_file(tmp_path):
    f = tmp_path / "state.json"
    mgr = StateManager(f)

    assert mgr.get_language() == "zh_CN"  # default
    assert f.exists() is False  # no auto-create on load


def test_set_and_get_language(tmp_path):
    f = tmp_path / "state.json"
    mgr = StateManager(f)

    mgr.set_language("en_US")
    assert mgr.get_language() == "en_US"

    # Ensure file was actually written
    assert f.exists()
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["lang"] == "en_US"


def test_load_existing_state(tmp_path):
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"lang": "ja_JP"}), encoding="utf-8")

    mgr = StateManager(f)
    assert mgr.get_language() == "ja_JP"


def test_load_invalid_json(tmp_path):
    f = tmp_path / "state.json"
    f.write_text("{not a json", encoding="utf-8")

    mgr = StateManager(f)
    assert mgr.get_language() == "zh_CN"  # fallback to default
    # Writing should overwrite invalid file
    mgr.set_language("ko_KR")
    assert json.loads(f.read_text(encoding="utf-8"))["lang"] == "ko_KR"


def test_save_creates_parent_dirs(tmp_path):
    nested_dir = tmp_path / "a/b/c"
    f = nested_dir / "state.json"

    mgr = StateManager(f)
    mgr.set_language("fr_FR")

    assert f.exists()
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["lang"] == "fr_FR"
