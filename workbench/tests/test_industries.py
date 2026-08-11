"""行业研究模块测试：种子加载、版本化、7 天清理、API 数据。"""
import datetime as dt
import json
import os

from app import industries, storage


def test_seed_loads(tmp_path, monkeypatch):
    """首次使用：从种子数据初始化当前版本。"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    cur = industries.current()
    assert len(cur["industries"]) == 30
    assert len(cur["cross_sectors"]) == 8
    assert cur["updated"]
    # 种子已复制到数据目录
    assert os.listdir(os.path.join(tmp_path, "industries"))


def test_get_industry_detail(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = industries.get_industry("ai-models")
    assert d["name"]
    assert d["jobs"] and d["investment"]


def test_get_industry_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    try:
        industries.get_industry("no-such")
        assert False
    except KeyError:
        pass


def test_history_and_prune(tmp_path, monkeypatch):
    """历史版本列表 + 超过 7 天的版本被清理。"""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    industries._ensure_initialized()
    # 手工写入一个 8 天前的旧版本
    old = dt.date.today() - dt.timedelta(days=8)
    old_path = industries._version_path(old.isoformat())
    os.makedirs(os.path.dirname(old_path), exist_ok=True)
    with open(old_path, "w", encoding="utf-8") as f:
        json.dump({"updated": old.isoformat(), "industries": [], "cross_sectors": []}, f, ensure_ascii=False)
    industries._prune_old()
    hist = industries.history()
    assert all(h["date"] != old.isoformat() for h in hist)


def test_seed_has_all_required_fields():
    """种子数据字段完整性。"""
    import json as _json
    with open(industries.SEED_PATH, encoding="utf-8") as f:
        seed = _json.load(f)
    required = {"name", "category", "prospects", "signs", "forecast", "jobs", "investment"}
    for ind in seed["industries"]:
        missing = required - set(ind.keys())
        assert not missing, f"{ind.get('name')} 缺字段: {missing}"
        assert ind["signs"], f"{ind['name']} 的 signs 为空"
