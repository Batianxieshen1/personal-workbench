"""雅思生词本：艾宾浩斯间隔复习。

复习节奏：添加后第 1 / 3 / 7 / 14 / 30 天各复习一次，全部完成即"毕业"。

词条结构：
{
  "id": "a1b2c3d4",
  "word": "abandon",
  "meaning": "v. 放弃",
  "added": "2026-08-03",   # 添加日期
  "stage": 0,               # 已完成复习次数
  "next": "2026-08-04",     # 下次复习日期；毕业为 null
}

设计要点：
- _next_date 是纯函数（stage + base 日期 → 下次复习日期），日期注入便于测试
- review 打卡以"当天"为基准推进下一阶段：今天复习完，N 天后回来
- 到期判断用字符串比较（ISO 格式 YYYY-MM-DD 字典序 = 时间序），避免时区坑
"""
import datetime as dt
import uuid

from . import storage

REVIEW_INTERVALS = [1, 3, 7, 14, 30]
VOCAB_FILE = "vocab.json"

# ── 内置雅思高频词库（按主题分组，一键导入免手动录入） ──
BUILTIN_WORDS = {
    "教育": [
        ("curriculum", "n. 课程"), ("tuition", "n. 学费"), ("scholarship", "n. 奖学金"),
        ("assessment", "n. 评估"), ("literacy", "n. 读写能力"), ("vocational", "adj. 职业的"),
        ("compulsory", "adj. 义务的，强制的"), ("critical", "adj. 批判性的；关键的"),
        ("memorise", "v. 记忆"), ("pedagogy", "n. 教学法"),
    ],
    "科技": [
        ("artificial", "adj. 人工的"), ("algorithm", "n. 算法"), ("automation", "n. 自动化"),
        ("breakthrough", "n. 突破"), ("digital", "adj. 数字的"), ("innovation", "n. 创新"),
        ("obsolete", "adj. 过时的"), ("privacy", "n. 隐私"), ("surveillance", "n. 监控"),
        ("virtual", "adj. 虚拟的"),
    ],
    "环境": [
        ("biodiversity", "n. 生物多样性"), ("carbon", "n. 碳"), ("climate", "n. 气候"),
        ("conservation", "n. 保护"), ("ecosystem", "n. 生态系统"), ("emission", "n. 排放"),
        ("renewable", "adj. 可再生的"), ("sustainable", "adj. 可持续的"), ("pollution", "n. 污染"),
        ("deforestation", "n. 滥伐森林"),
    ],
    "社会": [
        ("demographic", "adj. 人口的"), ("equality", "n. 平等"), ("generation", "n. 一代人"),
        ("inequality", "n. 不平等"), ("urbanisation", "n. 城市化"), ("welfare", "n. 福利"),
        ("community", "n. 社区"), ("diversity", "n. 多样性"), ("migration", "n. 迁移"),
        ("poverty", "n. 贫困"),
    ],
    "工作": [
        ("colleague", "n. 同事"), ("deadline", "n. 截止日期"), ("entrepreneur", "n. 企业家"),
        ("flexible", "adj. 灵活的"), ("promotion", "n. 晋升"), ("recruit", "v. 招聘"),
        ("salary", "n. 薪水"), ("workload", "n. 工作量"), ("remuneration", "n. 报酬"),
        ("occupation", "n. 职业"),
    ],
    "生活": [
        ("balanced", "adj. 均衡的"), ("commute", "v./n. 通勤"), ("convenience", "n. 便利"),
        ("diet", "n. 饮食"), ("leisure", "n. 休闲"), ("nutrition", "n. 营养"),
        ("routine", "n. 日常惯例"), ("wellbeing", "n. 幸福感"), ("lifestyle", "n. 生活方式"),
        ("recreation", "n. 娱乐"),
    ],
}


def _today() -> dt.date:
    return dt.date.today()


def _next_date(stage: int, base: dt.date) -> str | None:
    """第 stage 次复习后，下一次复习日期；stage 超过间隔表长度则毕业。"""
    if stage >= len(REVIEW_INTERVALS):
        return None
    return (base + dt.timedelta(days=REVIEW_INTERVALS[stage])).isoformat()


def _data() -> dict:
    return storage.load(VOCAB_FILE, {"words": []})


def _save(data: dict) -> None:
    storage.save(VOCAB_FILE, data)


def list_words() -> list:
    return _data()["words"]


def add_word(word: str, meaning: str) -> dict:
    w = {
        "id": uuid.uuid4().hex[:8],
        "word": word.strip(),
        "meaning": meaning.strip(),
        "added": _today().isoformat(),
        "stage": 0,
        "next": _next_date(0, _today()),
    }
    data = _data()
    data["words"].append(w)
    _save(data)
    return w


def update_meaning(word_id: str, meaning: str) -> dict:
    data = _data()
    for w in data["words"]:
        if w["id"] == word_id:
            w["meaning"] = meaning.strip()
            _save(data)
            return w
    raise KeyError(word_id)


def review(word_id: str, known: bool = True) -> dict:
    """复习打卡。

    known=True：认识，stage +1，按新 stage 排下一次复习
    known=False：不认识，stage 重置回 0（重新走一遍间隔）——真正的艾宾浩斯
    """
    data = _data()
    for w in data["words"]:
        if w["id"] == word_id:
            w["stage"] = w["stage"] + 1 if known else 0
            w["next"] = _next_date(w["stage"], _today())
            _save(data)
            return w
    raise KeyError(word_id)


def delete_word(word_id: str) -> None:
    data = _data()
    before = len(data["words"])
    data["words"] = [w for w in data["words"] if w["id"] != word_id]
    if len(data["words"]) == before:
        raise KeyError(word_id)
    _save(data)


def due_words(today: str | None = None) -> list:
    """到期队列：next <= today 且未毕业（next 非 null）。"""
    t = today or _today().isoformat()
    return [w for w in list_words() if w["next"] is not None and w["next"] <= t]


def import_builtin(limit: int | None = None) -> int:
    """一键导入内置词库（跳过已存在的词），返回新导入数量。"""
    existing = {w["word"] for w in list_words()}
    added = 0
    for topic, words in BUILTIN_WORDS.items():
        for word, meaning in words:
            if word in existing:
                continue
            add_word(word, meaning)
            added += 1
            existing.add(word)
            if limit and added >= limit:
                return added
    return added
