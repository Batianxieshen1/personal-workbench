"""
抖音解析报告 → Obsidian 笔记归档
把 douyin_extract.py 生成的 <id>_full.txt 转成带 YAML frontmatter 的标准笔记，
写入 Obsidian 知识库的 07-抖音视频/ 目录，并维护索引文件。

用法：
  python report_to_note.py <report.txt 或 video_id> [选项]

选项：
  --vault DIR        知识库根目录（优先级：--vault > DOUYIN_VAULT_DIR 环境变量 > ~/Desktop/agent/我的知识库）
  --summary FILE     「核心要点」markdown 片段（AI 通读字幕后撰写）
  --transcript FILE  整理后的字幕（分段+标点），原始转写折叠保留
  --no-index         不更新索引
  --force            同视频ID已存在时覆盖
  --dry-run          只打印将写入的内容，不落盘（确认制预览）

工作流约定（确认制）：
  1. 先 --dry-run 生成预览 → 用户看过确认 → 去掉 --dry-run 正式写入
  2. 按 视频ID 去重，重复归档自动跳过
"""
import argparse
import ast
import os
import re
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_VAULT = (
    os.environ.get("DOUYIN_VAULT_DIR")
    or os.path.join(os.path.expanduser("~"), "Desktop", "agent", "我的知识库")
)
NOTES_DIR = "07-抖音视频"
INDEX_NAME = "抖音视频索引"

# ── 报告解析 ───────────────────────────────────────────────

def parse_report(path):
    """解析 <id>_full.txt，返回 (元数据dict, 话题list, ocrlist, 字幕str, video_id, 提取日期)"""
    text = Path(path).read_text(encoding="utf-8")

    meta = {}
    m = re.search(r"【元数据】\n(.*?)\n【", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if ": " in line:
                k, v = line.split(": ", 1)
                meta[k] = v.strip()

    tags = []
    if "话题" in meta:
        try:
            tags = ast.literal_eval(meta["话题"])
        except Exception:
            tags = [t.strip() for t in meta["话题"].split(",") if t.strip()]

    ocr = []
    m = re.search(r"【画面OCR文字】\n(.*?)\n【", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            om = re.match(r"\s*\[(\d+)s\]\s*(.+)", line)
            if om:
                ocr.append((int(om.group(1)), om.group(2).strip()))

    transcript = ""
    m = re.search(r"【语音字幕全文】\n(.*)$", text, re.S)
    if m:
        transcript = m.group(1).strip()

    # 视频ID 从报告文件名取（<id>_full.txt），提取日期取文件修改时间
    vid = Path(path).name.replace("_full.txt", "")
    extract_date = datetime.fromtimestamp(Path(path).stat().st_mtime).strftime("%Y-%m-%d")
    return meta, [str(t) for t in tags], ocr, transcript, vid, extract_date

# ── 笔记构建 ───────────────────────────────────────────────

def sanitize_title(title, maxlen=28):
    """去掉话题标签尾巴和文件系统非法字符"""
    title = title.split(" #")[0]  # 截掉 "#AI产品经理 #程序员 ..." 标签串
    s = re.sub(r'[\\/:*?"<>|#\[\]]', "", title)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen].strip(" ,，.。") or "未命名"

def safe_tag(tag):
    return re.sub(r'[\s#/\\\[\]:]', "", tag)

def build_note(meta, tags, ocr, transcript, vid, extract_date,
               summary=None, polished=None):
    today = datetime.now().strftime("%Y-%m-%d")
    title = meta.get("标题", "未命名")
    author = meta.get("作者", "")
    author_id = meta.get("作者ID", "")
    url = f"https://www.douyin.com/video/{vid}"

    fm_tags = [safe_tag(t) for t in tags if safe_tag(t)]
    all_tags = ["抖音", "视频笔记"] + fm_tags
    lines = [
        "---",
        f"tags: [{', '.join(all_tags)}]",
        f"source: 抖音 @{author_id} 《{sanitize_title(title, 50)}》 {url}",
        f"date: {extract_date}",
        f"作者: {author}",
        f'视频ID: "{vid}"',
        f"时长秒: {meta.get('时长(秒)', 0)}",
        f"点赞: {meta.get('点赞', 0)}",
        f"评论: {meta.get('评论', 0)}",
        f"收藏: {meta.get('收藏', 0)}",
        f"分享: {meta.get('分享', 0)}",
        f"归档日期: {today}",
        "状态: 已归档",
        "---",
        "",
        f"# {title.split(' #')[0].strip()}",
        "",
        "> [!info] 视频卡片",
        f"> **作者**：{author}（@{author_id}） · **时长**：{meta.get('时长(秒)', 0)}s",
        f"> 👍 {meta.get('点赞', 0)} · 💬 {meta.get('评论', 0)} · ⭐ {meta.get('收藏', 0)} · 🔁 {meta.get('分享', 0)}",
        f"> 🔗 [原视频]({url})",
        "",
        "## 📝 核心要点",
        summary or "> [!todo] 待整理：通读字幕后，在这里补充 3-5 条要点",
        "",
        "## 🎙️ 字幕",
    ]
    if polished:
        lines += [polished, "", "> [!quote]- 原始转写（未断句）"]
        lines += ["> " + ln for ln in transcript.splitlines() or [""]]
    else:
        lines.append(transcript)
    if ocr:
        lines += ["", "## 🔍 画面文字（OCR）"]
        lines += [f"- **[{t}s]** {text}" for t, text in ocr]
    lines += [
        "",
        "## 🔗 关联",
        f"- [[{INDEX_NAME}]] · 提取 {extract_date} · 归档 {today}",
        "",
    ]
    return "\n".join(lines)

# ── 索引与写入 ─────────────────────────────────────────────

def find_existing(notes_dir, vid):
    """按 frontmatter 里的 视频ID 查重"""
    for f in notes_dir.glob("*.md"):
        if f.name == f"{INDEX_NAME}.md":
            continue
        if f'视频ID: "{vid}"' in f.read_text(encoding="utf-8", errors="ignore"):
            return f
    return None

def update_index(notes_dir, note_name, meta, extract_date):
    """维护索引表格，不存在则创建"""
    index_path = notes_dir / f"{INDEX_NAME}.md"
    row = (f"| {extract_date} | [[{note_name[:-3]}]] | @{meta.get('作者ID', '')} "
           f"| {meta.get('点赞', 0)} | {meta.get('评论', 0)} |")
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8").rstrip() + "\n"
    else:
        content = (
            f"# 🎬 抖音视频索引\n\n"
            f"由 douyin-extract skill 自动归档，按提取日期倒序。\n\n"
            f"| 提取日期 | 笔记 | 作者 | 👍 | 💬 |\n|---|---|---|---|---|\n"
        )
    content += row + "\n"
    index_path.write_text(content, encoding="utf-8")
    return index_path

# ── 主流程 ─────────────────────────────────────────────────

def resolve_report(arg):
    """参数可以是报告路径，也可以是裸视频ID（在 ./douyin_output 下找）"""
    p = Path(arg)
    if p.is_file():
        return p
    candidate = Path("douyin_output") / f"{arg}_full.txt"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"找不到报告文件: {arg}")

def main():
    ap = argparse.ArgumentParser(description="抖音解析报告 → Obsidian 笔记")
    ap.add_argument("report", help="报告路径或视频ID")
    ap.add_argument("--vault", default=DEFAULT_VAULT, help="知识库根目录")
    ap.add_argument("--summary", help="核心要点 markdown 文件")
    ap.add_argument("--transcript", help="整理后的字幕文件")
    ap.add_argument("--no-index", action="store_true", help="不更新索引")
    ap.add_argument("--force", action="store_true", help="覆盖已有笔记")
    ap.add_argument("--dry-run", action="store_true", help="只预览不写入")
    args = ap.parse_args()

    report_path = resolve_report(args.report)
    meta, tags, ocr, transcript, vid, extract_date = parse_report(report_path)

    summary = Path(args.summary).read_text(encoding="utf-8").strip() if args.summary else None
    polished = Path(args.transcript).read_text(encoding="utf-8").strip() if args.transcript else None

    note = build_note(meta, tags, ocr, transcript, vid, extract_date, summary, polished)
    filename = f"{extract_date} {sanitize_title(meta.get('标题', '未命名'))}.md"

    notes_dir = Path(args.vault) / NOTES_DIR
    notes_dir.mkdir(parents=True, exist_ok=True)
    target = notes_dir / filename

    existing = find_existing(notes_dir, vid)
    if existing and not args.force:
        print(f"[SKIP] 该视频已归档: {existing}")
        print("(如需覆盖请加 --force)")
        return

    if args.dry_run:
        print("=" * 60)
        print("  [DRY-RUN 预览] 以下内容将写入，未落盘")
        print("=" * 60)
        print(f"\n目标位置: {target}\n")
        print(note)
        if not args.no_index:
            print("\n" + "=" * 60)
            print(f"同时更新索引: {notes_dir / (INDEX_NAME + '.md')}")
            print(f"新增行: | {extract_date} | [[{filename[:-3]}]] | @{meta.get('作者ID','')} "
                  f"| {meta.get('点赞',0)} | {meta.get('评论',0)} |")
        return

    target.write_text(note, encoding="utf-8")
    print(f"[OK] 笔记已写入: {target}")
    if not args.no_index:
        index_path = update_index(notes_dir, filename, meta, extract_date)
        print(f"[OK] 索引已更新: {index_path}")

if __name__ == "__main__":
    main()
