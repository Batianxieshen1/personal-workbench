"""雅思 AI 练习：作文批改 + 口语模拟考官（DeepSeek，手动触发）。

成本：每次调用约 1-2 分钱，仅用户点击时消耗。
"""
from . import deepseek

SPEAKING_TOPICS = ["家乡", "工作与学习", "兴趣爱好", "科技", "环境", "旅行", "食物", "朋友", "健康"]

_ESSAY_SYSTEM = "你是资深雅思写作考官（9 分水平）。按雅思官方四项评分标准批改，用简洁中文回复。"


def essay_review(essay: str, topic: str = "") -> dict:
    """AI 批改雅思作文：四项打分 + 优点 + 建议。"""
    if not essay.strip():
        raise ValueError("作文内容为空")
    prompt = (
        f"题目：{topic or '（未提供题目）'}\n\n学生作文：\n{essay}\n\n"
        "请按雅思写作评分标准批改，回复格式：\n"
        "1. 四项得分（任务回应/连贯与衔接/词汇资源/语法，各 0-9）\n"
        "2. 总分\n3. 优点（2 条）\n4. 改进建议（3 条，具体可执行）"
    )
    review = deepseek.chat(prompt, system=_ESSAY_SYSTEM)
    return {"review": review}


def speaking_questions(topic: str) -> dict:
    """AI 考官出 3 个 Part1 问题（难度递进）。"""
    prompt = (
        f"你是雅思考官，进行口语 Part1 模拟，话题：{topic}。\n"
        "请出 3 个问题（从简单到深入），严格按以下格式输出：\n"
        "问题1：...\n问题2：...\n问题3：..."
    )
    text = deepseek.chat(prompt, system="你是雅思考官，用中文出题，语言自然口语化。")
    questions = [ln.split("：", 1)[1].strip() for ln in text.splitlines() if ln.startswith("问题")]
    return {"topic": topic, "questions": questions or [text]}


def speaking_review(topic: str, answers: str) -> dict:
    """AI 点评口语回答：四项标准 + 发音提示。"""
    if not answers.strip():
        raise ValueError("回答内容为空")
    prompt = (
        f"口语话题：{topic}\n\n我的回答：\n{answers}\n\n"
        "请按雅思口语四项标准点评（流利度与连贯/词汇/语法/发音提示），"
        "每项给 0-9 分 + 一句具体改进建议。"
    )
    review = deepseek.chat(prompt, system=_ESSAY_SYSTEM)
    return {"review": review}
