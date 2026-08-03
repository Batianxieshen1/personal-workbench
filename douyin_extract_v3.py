"""
抖音视频深度解析 v3.0
模块化设计：元数据 / OCR(可选) / 语音转文字 / AI摘要

用法：
  python douyin_extract_v3.py <video_id> [--ocr]
  Cookie 自动从 .douyin_cookie 文件读取，无需每次手动输入
  也可手动指定: python douyin_extract_v3.py <video_id> --cookie "<cookie_str>" [--ocr]
"""
import requests
import json
import subprocess
import sys
import os
import re
import imageio_ffmpeg
import numpy as np

# ── 配置 ───────────────────────────────────────────────────
OUTPUT_DIR = "douyin_output"
COOKIE_FILE = ".douyin_cookie"  # Cookie 缓存文件

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.douyin.com/",
}

# OCR 配置（仅当 --ocr 时使用）
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA_DIR = r"C:\Users\暴龙战士wink\tessdata"
OCR_LANG = 'chi_sim+eng'

# ── Cookie 管理 ────────────────────────────────────────────

def load_cookie(manual_cookie=None):
    """
    加载 Cookie，优先级：
    1. 手动传入的 cookie 字符串
    2. .douyin_cookie 文件
    如果都没有，报错并提示如何获取
    """
    if manual_cookie:
        return manual_cookie.strip()

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            cookie = f.read().strip()
        if cookie:
            return cookie

    raise RuntimeError(
        "未找到Cookie。请：\n"
        "  1. 浏览器打开 douyin.com 并登录\n"
        "  2. F12 → Network → 搜 'aweme' → 点请求 → 复制Cookie值\n"
        "  3. 运行: python douyin_extract_v3.py <id> --cookie \"你的Cookie\"\n"
        "或手动创建 .douyin_cookie 文件放入Cookie"
    )
FRAME_INTERVAL = 8  # 每 N 秒抽一帧

# ── 工具函数 ───────────────────────────────────────────────

def get_ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()

def patch_whisper_ffmpeg(ffmpeg_bin):
    """Monkey-patch whisper 用的 subprocess.run，指向本地 ffmpeg"""
    _orig = subprocess.run
    def patched(cmd_args, **kw):
        if isinstance(cmd_args, list) and cmd_args[0] == 'ffmpeg':
            cmd_args = [ffmpeg_bin] + cmd_args[1:]
        return _orig(cmd_args, **kw)
    subprocess.run = patched

def load_audio_manual(ffmpeg_bin, file_path, sr=16000):
    """绕过 whisper 内部 ffmpeg 调用"""
    proc = subprocess.Popen(
        [ffmpeg_bin, '-i', file_path, '-f', 's16le', '-acodec', 'pcm_s16le',
         '-ar', str(sr), '-ac', '1', '-'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    out, _ = proc.communicate()
    return np.frombuffer(out, np.int16).astype(np.float32) / 32768.0

# ── Step 1: 元数据提取 ─────────────────────────────────────

def extract_metadata(video_id, cookie):
    """调用抖音 API 获取视频元数据"""
    headers = {**HEADERS_BASE, "Cookie": cookie}
    api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}&aid=6383"
    resp = requests.get(api_url, headers=headers, timeout=15)
    data = resp.json()
    if "aweme_detail" not in data:
        raise RuntimeError(f"API返回异常，请检查Cookie是否过期: {str(data)[:200]}")
    return data["aweme_detail"]

def format_metadata(detail):
    """将 API 原始数据转成结构化字典"""
    author = detail.get("author", {})
    stats = detail.get("statistics", {})
    tags = []
    for t in detail.get("text_extra", []):
        tag = t.get("hashtag_name") or t.get("title", "")
        if tag:
            tags.append(tag)
    return {
        "标题": detail.get("desc", ""),
        "作者": author.get("nickname", ""),
        "作者ID": author.get("unique_id", ""),
        "话题": tags,
        "时长(秒)": detail.get("duration", 0) // 1000,
        "点赞": stats.get("digg_count", 0),
        "评论": stats.get("comment_count", 0),
        "收藏": stats.get("collect_count", 0),
        "分享": stats.get("share_count", 0),
    }

# ── Step 2: 视频下载 ───────────────────────────────────────

def get_video_url(detail):
    """从 API 结果中提取最高画质视频链接"""
    video_info = detail["video"]
    if "bit_rate" in video_info and video_info["bit_rate"]:
        best = max(video_info["bit_rate"], key=lambda x: x.get("bit_rate", 0))
        return best["play_addr"]["url_list"][0]
    return video_info["play_addr"]["url_list"][0]

def download_video(video_url, video_path, cookie):
    """流式下载视频，跳过已存在文件"""
    if os.path.exists(video_path):
        return False  # 已存在，跳过
    headers = {**HEADERS_BASE, "Cookie": cookie}
    resp = requests.get(video_url, headers=headers, stream=True, timeout=120)
    with open(video_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return True  # 新下载

# ── Step 3: OCR 画面文字提取（可选） ────────────────────────

def extract_frames_and_ocr(video_path, frames_dir, total_sec, ffmpeg_bin):
    """从视频中抽帧 + Tesseract OCR，返回 [(时间秒, 文字), ...]"""
    try:
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR
    except ImportError:
        print("  [WARN] pytesseract/Pillow 未安装，跳过OCR")
        return []

    intervals = list(range(3, min(total_sec, 180), FRAME_INTERVAL))
    if not intervals:
        return []

    os.makedirs(frames_dir, exist_ok=True)
    results = []

    for t in intervals:
        frame_path = os.path.join(frames_dir, f"frame_{t:04d}s.png")
        subprocess.run(
            [ffmpeg_bin, '-ss', str(t), '-i', video_path,
             '-vframes', '1', '-q:v', '2', frame_path, '-y'],
            capture_output=True
        )
        if os.path.exists(frame_path) and os.path.getsize(frame_path) > 1000:
            try:
                img = Image.open(frame_path)
                text = pytesseract.image_to_string(img, lang=OCR_LANG).strip()
                text = re.sub(r'\s+', ' ', text)
                if len(text) > 2:
                    results.append((t, text))
            except Exception:
                pass

    # 去重
    seen = set()
    unique = []
    for t, text in results:
        key = re.sub(r'\s+', '', text)[:30]
        if key and key not in seen:
            seen.add(key)
            unique.append((t, text))
    return unique

# ── Step 4: Whisper 语音转文字 ─────────────────────────────

def extract_audio(video_path, audio_path, ffmpeg_bin):
    """从视频中提取 WAV 音频"""
    if not os.path.exists(audio_path):
        subprocess.run(
            [ffmpeg_bin, '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
             '-ar', '16000', '-ac', '1', audio_path, '-y'],
            capture_output=True
        )

def transcribe_audio(audio_path, ffmpeg_bin):
    """Whisper 语音转文字"""
    import whisper
    patch_whisper_ffmpeg(ffmpeg_bin)
    whisper.audio.load_audio = lambda fp, sr=16000: load_audio_manual(ffmpeg_bin, fp, sr)
    model = whisper.load_model("small")
    result = model.transcribe(audio_path, language="zh")
    return result["text"]

# ── 主流程 ─────────────────────────────────────────────────

def run(video_id, cookie, enable_ocr=False):
    ffmpeg_bin = get_ffmpeg()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    video_path = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
    audio_path = os.path.join(OUTPUT_DIR, f"{video_id}.wav")
    report_path = os.path.join(OUTPUT_DIR, f"{video_id}_full.txt")

    print("=" * 60)
    print("  抖音视频深度解析 v3.0" + (" (含OCR)" if enable_ocr else ""))
    print("=" * 60)

    # Step 1: 元数据
    print("\n[1/4] 提取元数据...")
    detail = extract_metadata(video_id, cookie)
    metadata = format_metadata(detail)
    print(f"  标题: {metadata['标题']}")
    print(f"  作者: {metadata['作者']} (@{metadata['作者ID']})")
    print(f"  话题: {', '.join(metadata['话题'])}")
    print(f"  时长: {metadata['时长(秒)']}s | likes={metadata['点赞']} comments={metadata['评论']} collects={metadata['收藏']}")

    # Step 2: 下载
    print("\n[2/4] 下载视频...")
    video_url = get_video_url(detail)
    is_new = download_video(video_url, video_path, cookie)
    size_mb = os.path.getsize(video_path) // 1024 // 1024
    print(f"  {'已保存' if is_new else '已存在'} ({size_mb}MB)")

    # Step 3: OCR（可选）
    ocr_results = []
    if enable_ocr:
        print("\n[3/4] OCR 画面文字识别...")
        frames_dir = os.path.join(OUTPUT_DIR, f"frames_{video_id}")
        ocr_results = extract_frames_and_ocr(video_path, frames_dir, metadata['时长(秒)'], ffmpeg_bin)
        print(f"  提取了 {metadata['时长(秒)'] // FRAME_INTERVAL} 帧, 检测到 {len(ocr_results)} 段文字")
        step_num = 4
    else:
        print("\n[3/4] 跳过OCR (口播/真人出镜类视频按需开启)")
        step_num = 3

    # Step N: Whisper
    print(f"\n[{step_num}/4] 语音转文字...")
    extract_audio(video_path, audio_path, ffmpeg_bin)
    transcript = transcribe_audio(audio_path, ffmpeg_bin)

    # 保存报告
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 50 + "\n")
        f.write("  抖音视频深度解析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write("【元数据】\n")
        for k, v in metadata.items():
            f.write(f"  {k}: {v}\n")
        if enable_ocr and ocr_results:
            f.write("\n【画面OCR文字】\n")
            for t, text in ocr_results:
                f.write(f"  [{t}s] {text}\n")
        else:
            f.write("\n【画面OCR文字】\n  (未开启)\n")
        f.write("\n【语音字幕全文】\n")
        f.write(transcript + "\n")

    print(f"\n[OK] 报告已保存: {report_path}")

    # 输出摘要供 AI 后续处理
    return {
        "metadata": metadata,
        "ocr": ocr_results,
        "transcript": transcript,
        "report_path": report_path,
    }

# ── CLI入口 ─────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python douyin_extract_v3.py <video_id> [--ocr]")
        print("  python douyin_extract_v3.py <video_id> --cookie \"<cookie_str>\" [--ocr]")
        print("")
        print("Cookie 自动从 .douyin_cookie 读取，无需每次手动输入")
        sys.exit(1)

    video_id = sys.argv[1]

    # 解析 --cookie 参数
    manual_cookie = None
    args = sys.argv[2:]
    if "--cookie" in args:
        idx = args.index("--cookie")
        if idx + 1 < len(args):
            manual_cookie = args[idx + 1]

    enable_ocr = "--ocr" in sys.argv

    cookie = load_cookie(manual_cookie)
    result = run(video_id, cookie, enable_ocr)

    # 输出结构化JSON 供后续处理
    print("\n--- JSON_OUTPUT ---")
    print(json.dumps({
        "metadata": result["metadata"],
        "ocr_count": len(result["ocr"]),
        "transcript_length": len(result["transcript"]),
    }, ensure_ascii=False))
