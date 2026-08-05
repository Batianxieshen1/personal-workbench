"""配置模块测试：默认值、改昵称、改城市（地理编码被 mock）。"""
import pytest

from app import config, storage


def test_default_config(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    cfg = config.get_config()
    assert cfg["nickname"] == "同学"
    assert cfg["lat"] is not None and cfg["lon"] is not None


def test_set_nickname(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    config.set_nickname("  小暴龙  ")
    assert config.get_config()["nickname"] == "小暴龙"


def test_set_city_geocodes_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config.weather, "geocode_city",
                        lambda name, timeout=5.0: {"city": "深圳", "lat": 22.5431, "lon": 114.0579})
    config.set_city("深圳")
    cfg = config.get_config()
    assert cfg["city"] == "深圳"
    assert cfg["lat"] == 22.5431
    assert cfg["lon"] == 114.0579


def test_set_city_not_found_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config.weather, "geocode_city", lambda name, timeout=5.0: None)
    try:
        config.set_city("不存在的城市")
        assert False, "应当抛出 ValueError"
    except ValueError:
        pass
    # 失败的修改不能污染已存配置
    assert config.get_config()["city"] != "不存在的城市"


def test_language_default_and_set(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    assert config.get_config()["language"] == "zh"
    config.set_language("en")
    assert config.get_config()["language"] == "en"
    with pytest.raises(ValueError):  # 非法值拒绝且不写盘
        config.set_language("fr")
    assert config.get_config()["language"] == "en"
