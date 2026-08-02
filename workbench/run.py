"""一键启动：python run.py → 起服务 + 自动打开浏览器。

要点：
- 用线程延迟 1.2 秒开浏览器：等 uvicorn 把端口监听起来再访问，避免白屏
- uvicorn.run 的 reload=False：本地个人使用不需要热重载，省资源
"""
import threading
import time
import webbrowser

import uvicorn

PORT = 8765


def _open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="info")
