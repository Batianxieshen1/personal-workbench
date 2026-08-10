"""一键启动：python run.py → 起服务 + 自动打开浏览器。

要点：
- 绑定 0.0.0.0 监听所有网卡：局域网内手机/平板也能访问 http://<本机IP>:8765
- 自动探测本机局域网 IP 供浏览器打开（探测失败回退 127.0.0.1）
- 【端口自愈】启动前检测 8765 被占用：说明有旧服务进程残留，
  自动结束旧进程再启动（避免"改完代码不生效"）
- 【自动备份】每天首次启动自动备份一次 data/（数据安全）
- 用线程延迟 1.2 秒开浏览器：等 uvicorn 把端口监听起来再访问，避免白屏
"""
import datetime as dt
import os
import socket
import subprocess
import threading
import time
import webbrowser

import uvicorn

HOST = "0.0.0.0"
PORT = 8765
BASE = os.path.dirname(os.path.abspath(__file__))


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _kill_port_owner(port: int) -> None:
    """结束占用指定端口的进程（netstat 找 PID → taskkill）。"""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True,
                             text=True, encoding="locale", timeout=15).stdout
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.split()[-1]
                subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
                print(f"[i] 已结束占用端口 {port} 的旧进程 PID={pid}（避免旧代码残留）")
                return
    except Exception as e:
        print(f"[i] 端口清理失败（{e}），如仍无法启动请手动结束占用进程")


def _auto_backup() -> None:
    """每天首次启动自动备份一次 data/。"""
    try:
        from backup import backup
        marker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups", ".last")
        today = dt.date.today().isoformat()
        if os.path.exists(marker) and open(marker, encoding="utf-8").read() == today:
            return  # 今天已备份过
        path = backup()
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as f:
            f.write(today)
        print(f"[i] 已自动备份数据 → {path}")
    except Exception as e:
        print(f"[i] 自动备份跳过：{e}")


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
    if _port_in_use(PORT):
        _kill_port_owner(PORT)
        time.sleep(0.5)  # 等端口释放
    _auto_backup()
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")
