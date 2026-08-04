"""今日行动指南测试：规则引擎按优先级生成行动清单。"""
from app import guide, storage


def _seed(tmp_path, monkeypatch, **kw):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    # 默认：计划空、无到期词、无灵感、进度缺失、无总结
    monkeypatch.setattr(guide.plan, "get_plan", lambda d: {"date": d, "items": kw.get("plan_items", [])})
    monkeypatch.setattr(guide.vocab, "due_words", lambda today=None: kw.get("due", []))
    monkeypatch.setattr(guide.ideas, "get_today", lambda d: kw.get("ideas", []))
    monkeypatch.setattr(guide.progress, "load_progress",
                        lambda: kw.get("progress", {"missing": True, "done_count": 0, "total_count": 0}))
    monkeypatch.setattr(guide.reviews, "get_review", lambda d: {"summary": kw.get("summary", "")})


def test_all_pending_gives_full_guide(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch,
          progress={"missing": False, "done_count": 3, "total_count": 8},
          ideas=[{"id": "a", "source": "ai", "status": "kept"}])
    actions = guide.build_guide("2026-08-04")
    ids = [a["id"] for a in actions]
    assert ids == ["plan", "ideas", "study", "review"]  # 按优先级排序
    assert actions[0]["priority"] == 1
    assert actions[-1]["priority"] == 5


def test_plan_done_hides_plan_action(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, plan_items=[{"id": "x", "text": "写代码", "done": False}])
    actions = guide.build_guide("2026-08-04")
    assert "plan" not in [a["id"] for a in actions]
    assert "plan-start" in [a["id"] for a in actions]


def test_vocab_due_appears(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, due=[{"id": "w1"}])
    actions = guide.build_guide("2026-08-04")
    assert any(a["id"] == "vocab" and "1 个" in a["text"] for a in actions)


def test_ideas_processed_hidden(tmp_path, monkeypatch):
    # 已丢弃/已采用 → 不再提示
    _seed(tmp_path, monkeypatch,
          ideas=[{"id": "a", "source": "ai", "status": "discarded"},
                 {"id": "b", "source": "ai", "status": "done"}])
    assert "ideas" not in [a["id"] for a in guide.build_guide("2026-08-04")]


def test_review_written_hidden(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, summary="今天很充实")
    assert "review" not in [a["id"] for a in guide.build_guide("2026-08-04")]


def test_everything_done_empty(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch,
          plan_items=[{"id": "x", "text": "a", "done": True}],
          summary="写完了",
          ideas=[{"id": "a", "source": "ai", "status": "done"}],
          progress={"missing": False, "done_count": 8, "total_count": 8})
    assert guide.build_guide("2026-08-04") == []
