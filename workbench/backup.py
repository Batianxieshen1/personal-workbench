"""一键备份：把 data/ 打包成带日期的 zip，存到 backups/。

用法：python backup.py
备份文件名：backups/data-2026-08-03-153000.zip
"""
import datetime as dt
import os
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
BACKUP_DIR = os.path.join(BASE, "backups")


def backup() -> str:
    if not os.path.isdir(DATA_DIR):
        raise FileNotFoundError(f"数据目录不存在：{DATA_DIR}")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    path = os.path.join(BACKUP_DIR, f"data-{stamp}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(DATA_DIR):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, BASE)  # 相对 workbench/，保留 data/ 前缀
                zf.write(full, rel)
    return path


if __name__ == "__main__":
    try:
        p = backup()
        size_kb = os.path.getsize(p) // 1024
        print(f"[OK] 备份完成：{p}（{size_kb} KB）")
    except Exception as e:
        print(f"[ERR] 备份失败：{e}")
