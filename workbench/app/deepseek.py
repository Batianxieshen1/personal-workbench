"""DeepSeek API 客户端：OpenAI 兼容 chat 接口。

key 来源（优先级）：
1. 环境变量 DEEPSEEK_API_KEY
2. 项目根 .env 文件（DEEPSEEK_API_KEY=sk-xxx）

设计要点：
- 不引入 python-dotenv 依赖，手写 15 行解析器（够用即可，DRY）
- 所有失败统一抛 AIError（无 key / 网络错 / 空回复），上层捕获后降级
- AIError 带原因字段，方便前端显示"没配 key"还是"服务挂了"
"""
import os
import requests

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# workbench/ 的上级目录 = 项目根（.env 所在处）
ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env",
)


class AIError(Exception):
    """AI 调用失败：无 key / 网络错误 / 空回复。reason 区分原因。"""

    def __init__(self, message: str, reason: str = "unknown"):
        super().__init__(message)
        self.reason = reason


def get_api_key() -> str:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"].strip()
    # 懒加载 .env（只补缺的键，不覆盖已有环境变量）
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def chat(prompt: str, system: str = "", timeout: float = 60.0) -> str:
    """调用 DeepSeek chat 接口，返回助手回复文本（去除首尾空白）。"""
    key = get_api_key()
    if not key:
        raise AIError("未配置 DEEPSEEK_API_KEY（在项目根 .env 中设置）", reason="no_key")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": MODEL, "messages": messages, "temperature": 1.0},
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise AIError(f"DeepSeek 调用失败：{e}", reason="network")
    if not content:
        raise AIError("DeepSeek 返回空内容", reason="empty")
    return content
