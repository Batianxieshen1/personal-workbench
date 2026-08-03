"""雅思进度：目标分、当前水平、备考阶段、考试日期、四科单项。存 data/ielts.json。

设计要点：
- get_ielts() 永远返回完整结构（默认值打底），前端不用判空
- update_ielts 只接受白名单字段，未知字段静默忽略（防手滑传错）
- skills 是子字典，单独做浅合并：只改传进来的那几科
"""
from . import storage

IELTS_FILE = "ielts.json"

DEFAULTS = {
    "target_score": 6.5,
    "current_band": "5.5",
    "stage": "基础强化",
    "exam_date": "",
    "skills": {"听力": "", "阅读": "", "写作": "", "口语": ""},
}

_ALLOWED = {"target_score", "current_band", "stage", "exam_date", "skills"}


def get_ielts() -> dict:
    data = storage.load(IELTS_FILE, None) or {}
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in _ALLOWED and v is not None})
    merged["skills"] = {**DEFAULTS["skills"], **(data.get("skills") or {})}
    return merged


def update_ielts(patch: dict) -> dict:
    current = get_ielts()
    for k, v in patch.items():
        if k not in _ALLOWED or v is None:
            continue
        if k == "skills":
            current["skills"].update(v or {})
        else:
            current[k] = v
    storage.save(IELTS_FILE, current)
    return current
