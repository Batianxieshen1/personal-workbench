"""考公模块：广东省考 + 央国企备考。

- EXAM_INFO：考情速览（省考三类型/行测五模块/申论/央国企要点）
- 科目进度：data/exam.json 打卡
- AI 每日一练：选模块 → AI 出题 → 作答 → AI 判题解析（广东特色题型）
- 考试倒计时：设置目标日期
"""
import datetime as dt

from . import deepseek
from . import storage

EXAM_FILE = "exam.json"

EXAM_MODULES = ["政治理论", "常识应用", "数量关系", "判断推理", "科学推理", "资料分析", "申论小题"]

# ── 考情速览（信息来自用户整理的考公资料） ──
EXAM_INFO = {
    "province": {
        "title": "广东省考 · 笔试科目（按岗位三类）",
        "types": [
            {"name": "县级以上/一般岗位", "subjects": "行测 + 申论一"},
            {"name": "乡镇/街道基层", "subjects": "行测 + 申论二"},
            {"name": "行政执法类", "subjects": "行测 + 申论 + 行政执法专业科目"},
            {"name": "公安机关人民警察", "subjects": "行测 + 申论 + 公安专业科目"},
        ],
        "timeline": "公告 1 月发布 → 笔试 3 月 → 面试 4-5 月（结构化，笔试50%+面试50%）",
    },
    "xingce": {
        "title": "行测（90 分钟 / 100 题 / 100 分）",
        "modules": [
            {"name": "政治理论", "count": 10, "note": "习近平新时代中国特色社会主义思想、二十届三中全会精神、中央经济工作会议、广东省委部署（百千万工程、绿美广东）"},
            {"name": "常识应用", "count": 15, "note": "法律/历史/地理/科技/经济/文化百科，广东特色：本省省情考得多"},
            {"name": "数量关系", "count": 15, "note": "数字推理 + 数学运算（广东保留数字推理，国考已删）"},
            {"name": "判断推理", "count": 40, "note": "图形推理/类比推理/逻辑判断/科学推理（科推=初中理化，广东特色）"},
            {"name": "资料分析", "count": 20, "note": "统计图表 + 速算技巧"},
        ],
    },
    "shenlun": {
        "title": "申论（满分 100）",
        "notes": [
            {"name": "申论一（县级以上）", "note": "主题：高质量发展/制造业当家/改革开放；题型：归纳概括/综合分析/对策/大作文"},
            {"name": "申论二（乡镇街道）", "note": "主题：乡村振兴/基层治理/百千万工程；题型：应用文（发言稿/调研报告）+ 大作文"},
        ],
    },
    "state": {
        "title": "央国企招聘笔试（标准五件套）",
        "notes": [
            {"name": "行测/EPI", "note": "言语/数量/判断/资料（比省考简单），几乎全部企业都考"},
            {"name": "英语", "note": "单选+阅读，4 级上下难度；银行/运营商/外企型央企必考"},
            {"name": "综合知识", "note": "时政/经济金融常识/计算机基础/企业文化"},
            {"name": "专业知识", "note": "按岗位：电气/通信/计算机/财务/法律等；技术岗必考"},
            {"name": "性格测试", "note": "几百道心理测评，不计分但可能一票否决"},
        ],
        "key_enterprises": "广东重点盯：南方电网、广东烟草、广铁、运营商省公司、银行省分行（秋招 9-11 月、春招 3-5 月）",
    },
}


def _data() -> dict:
    return storage.load(EXAM_FILE, {"progress": {}, "exam_date": ""})


def _save(data: dict) -> None:
    storage.save(EXAM_FILE, data)


def get_progress() -> dict:
    return _data()


def set_progress(module: str, done: bool) -> dict:
    data = _data()
    data["progress"][module] = bool(done)
    _save(data)
    return data


def set_exam_date(date_str: str) -> dict:
    data = _data()
    data["exam_date"] = date_str
    _save(data)
    return data


def days_until_exam() -> int | None:
    d = _data()["exam_date"]
    if not d:
        return None
    try:
        return (dt.date.fromisoformat(d) - dt.date.today()).days
    except ValueError:
        return None


def ai_generate_question(module: str) -> dict:
    """AI 出一道广东特色题目（选择题）。

    答案与解析单独剥离到 answer/explain 字段（前端出题时不显示，
    判题时才揭示——避免题目+答案一起暴露）。
    """
    prompt = (
        f"你是广东省考出题老师。请出一道【{module}】模块的真题风格选择题（4 个选项），"
        "输出格式严格为：\n题目：...\nA. ...\nB. ...\nC. ...\nD. ...\n"
        "答案：X\n解析：...（150 字内）\n"
        "注意：「答案」和「解析」必须单独成行、放在最后，题目部分不要出现答案线索。"
    )
    content = deepseek.chat(prompt, system="你是广东省考出题老师，题目严谨、贴近真题，用中文。")
    # 剥离答案与解析：题目部分给用户看，答案解析留给判题
    answer, explain, clean = "", "", []
    for ln in content.splitlines():
        if ln.startswith("答案"):
            answer = ln.split("：", 1)[1].strip() if "：" in ln else ln[2:].strip()
        elif ln.startswith("解析"):
            explain = ln.split("：", 1)[1].strip() if "：" in ln else ""
        else:
            clean.append(ln)
    return {"module": module, "content": "\n".join(clean).strip(), "answer": answer, "explain": explain}


def ai_check_answer(module: str, question: str, user_answer: str, answer: str = "") -> dict:
    """AI 判题并解析（带标准答案则直接核对，不带则自行判断）。"""
    if not user_answer.strip():
        raise ValueError("请先作答")
    answer_line = f"标准答案：{answer}" if answer else "标准答案未知（请自行判断对错）"
    prompt = (
        f"模块：{module}\n题目：\n{question}\n\n{answer_line}\n\n我的答案：{user_answer}\n\n"
        "请判定对错：先说「回答正确 ✅」或「回答错误 ❌ 正确答案是X」，再给出简要解析。"
    )
    result = deepseek.chat(prompt, system="你是广东省考辅导老师，点评简洁准确。")
    return {"result": result}
