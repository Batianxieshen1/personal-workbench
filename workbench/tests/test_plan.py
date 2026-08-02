"""今日计划测试：按天存取、增删、勾选、空日期默认。"""
import datetime as dt

from app import plan, storage


def _today():
    return dt.date.today().isoformat()


def test_get_plan_missing_date_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    p = plan.get_plan(_today())
    assert p["date"] == _today()
    assert p["items"] == []


def test_add_item_then_get(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = _today()
    plan.add_item(d, "  背 50 个雅思单词  ")
    p = plan.get_plan(d)
    assert len(p["items"]) == 1
    assert p["items"][0]["text"] == "背 50 个雅思单词"  # 首尾空白被去掉
    assert p["items"][0]["done"] is False


def test_toggle_done(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = _today()
    plan.add_item(d, "学习大模型")
    item_id = plan.get_plan(d)["items"][0]["id"]
    plan.update_item(d, item_id, done=True)
    assert plan.get_plan(d)["items"][0]["done"] is True
    plan.update_item(d, item_id, done=False)
    assert plan.get_plan(d)["items"][0]["done"] is False


def test_edit_text(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = _today()
    plan.add_item(d, "旧内容")
    item_id = plan.get_plan(d)["items"][0]["id"]
    plan.update_item(d, item_id, text="新内容")
    assert plan.get_plan(d)["items"][0]["text"] == "新内容"


def test_delete_item(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = _today()
    plan.add_item(d, "要删除的")
    plan.add_item(d, "要保留的")
    victim = plan.get_plan(d)["items"][0]["id"]
    plan.delete_item(d, victim)
    items = plan.get_plan(d)["items"]
    assert len(items) == 1
    assert items[0]["text"] == "要保留的"


def test_update_missing_item_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    d = _today()
    try:
        plan.update_item(d, "no-such-id", done=True)
        assert False, "应当抛出 KeyError"
    except KeyError:
        pass


def test_days_are_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    plan.add_item("2026-08-01", "昨天的任务")
    plan.add_item("2026-08-02", "今天的任务")
    assert len(plan.get_plan("2026-08-01")["items"]) == 1
    assert plan.get_plan("2026-08-01")["items"][0]["text"] == "昨天的任务"
    assert len(plan.get_plan("2026-08-02")["items"]) == 1
