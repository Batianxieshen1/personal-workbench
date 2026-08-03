"""一键启动：python run.py → 起服务 + 自动打开浏览器。

要点：
- 绑定 0.0.0.0 监听所有网卡：局域网内手机/平板也能访问 http://<本机IP>:8765
- 自动探测本机局域网 IP 供浏览器打开（探测失败回退 127.0.0.1）
- 用线程延迟 1.2 秒开浏览器：等 uvicorn 把端口监听起来再访问，避免白屏
- uvicorn.run 的 reload=False：本地个人使用不需要热重载，省资源
"""
import socket
import threading
import time
import webbrowser

import uvicorn

HOST = "0.0.0.0"
PORT = 8765


def _local_ip() -> str:
    """探测本机局域网 IP：向外部地址建一个不发数据的 UDP 连接，
    内核会选一条出网路径，getsockname 返回这条路径上的本机 IP。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://{_local_ip()}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")
