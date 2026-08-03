"""Obsidian 联动 + 坐标配置测试。"""
from app import config, obsidian, storage


def test_daily_uri():
    uri = obsidian.daily_uri("2026-08-03")
    assert uri.startswith("obsidian://open?vault=")
    assert "2026-08-03" in uri
    assert "01-" in uri  # 日记目录


def test_vault_uri():
    assert obsidian.vault_uri().startswith("obsidian://open?vault=")


def test_set_coords(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    config.set_coords("梅州五华", 23.92961, 115.76499)
    cfg = config.get_config()
    assert cfg["city"] == "梅州五华"
    assert cfg["lat"] == 23.92961
    assert cfg["lon"] == 115.76499


def test_set_coords_does_not_break_other_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    config.set_nickname("小暴龙")
    config.set_coords("北京", 39.9, 116.4)
    assert config.get_config()["nickname"] == "小暴龙"
