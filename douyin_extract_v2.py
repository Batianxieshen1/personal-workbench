import requests
import json
import subprocess
import sys
import os
import re
import imageio_ffmpeg
import numpy as np
import pytesseract
from PIL import Image

# Tesseract config
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA_DIR = r"C:\Users\暴龙战士wink\tessdata"
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

VIDEO_ID = "7656065001418404723"
COOKIE = "bd_ticket_guard_client_web_domain=2; uid_tt=5c76092ee50c0843e5a7e418d9d82cdb; uid_tt_ss=5c76092ee50c0843e5a7e418d9d82cdb; sid_tt=0057c7cec80cc44503ae3397d59423b4; sessionid=0057c7cec80cc44503ae3397d59423b4; sessionid_ss=0057c7cec80cc44503ae3397d59423b4; is_staff_user=false; _bd_ticket_crypt_cookie=35dd845c945e5f5e6f83d68c5f2f57d2; live_use_vvc=%22false%22; hevc_supported=true; enter_pc_once=1; SEARCH_RESULT_LIST_TYPE=%22single%22; xgplayer_user_id=99517796221; UIFID_TEMP=834e8292a57169584b829a284cfad93df7bd06dccdbce3984f79b694b3d0c587fab7082bf3e25e7b92b1af849dea5b4868cdcc55557bafa3b29fc5cb215827f603697e9fb97afda0dcbea2019310e6ad21a80c2c46cd5d4d9c7f4212b8b47130; fpk1=U2FsdGVkX1+ZQdATLrM3wUm8xbIXjcRw3WNUPTgw0rFIxZp3MqI8dfILLiJe6MXHGiA3//0Q8+paTrhp23XWCA==; fpk2=9be3e00191ffcce29a6799859112a898; UIFID=834e8292a57169584b829a284cfad93df7bd06dccdbce3984f79b694b3d0c587fab7082bf3e25e7b92b1af849dea5b4868cdcc55557bafa3b29fc5cb215827f674d172838cd0ae181f123344c008e90109685bb34731f9f503e730e60d7fb4ef0a5526511e8c01b8010689a17393f7433561f7f9ab2adbfcc1db152b8045082b9a419d0904bd4c5213aff80dba30d6e157958e2e6de2cb7bff9dd289353c288a56661076106f1988a727e20fad983b20; UIFID=834e8292a57169584b829a284cfad93df7bd06dccdbce3984f79b694b3d0c587fab7082bf3e25e7b92b1af849dea5b4868cdcc55557bafa3b29fc5cb215827f674d172838cd0ae181f123344c008e90109685bb34731f9f503e730e60d7fb4ef0a5526511e8c01b8010689a17393f7433561f7f9ab2adbfcc1db152b8045082b9a419d0904bd4c5213aff80dba30d6e157958e2e6de2cb7bff9dd289353c288a4572420f3f4374d41576486a4f786d1bb9692c416e7d37ab7cd1a1cf2f11b34e; __itrace_wid=38210d21-8183-46b6-874b-43f773623c69; xgplayer_device_id=55972314661; my_rd=2; is_dash_user=1; has_biz_token=false; live_private_user=0; sid_guard=0057c7cec80cc44503ae3397d59423b4%7C1783328095%7C5184000%7CFri%2C+04-Sep-2026+08%3A54%3A55+GMT; s_v_web_id=verify_mrsuwl9m_CrjYE8pE_d8wQ_4ixl_Au9s_KoGF56EubjNL; passport_csrf_token=5d7ff41b0ef196a8e5c1a5401f3d6bbd; passport_csrf_token_default=5d7ff41b0ef196a8e5c1a5401f3d6bbd; bd_ticket_guard_ts_sign_id=6d48eb3d1f13f725a800; passport_auth_mix_state=a7yjs5uxuflnaxhmfrj7cqqfoa74x0y2; odin_tt=b58736e15a226cad084cde8b67696a4db81b0fcea1900b0fd4cec921f6d482e3df299807575a90359251c9d3ef574215da52fc54daa8daab78c027902332f5d8; ttwid=1%7C85c-HmAcGKLIsHqYlwWen8XZ-wHJknPPQHSFTDzS-SY%7C1785340847%7C9d00d108c8dfe8d964bcb7d09d1e76814156530d252bb103d5f3966f4d272192; IsDouyinActive=true"

OUTPUT_DIR = "douyin_output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, f"frames_{VIDEO_ID}")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.douyin.com/",
    "Cookie": COOKIE,
}

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
video_path = os.path.join(OUTPUT_DIR, f"{VIDEO_ID}.mp4")
audio_path = os.path.join(OUTPUT_DIR, f"{VIDEO_ID}.wav")
full_path = os.path.join(OUTPUT_DIR, f"{VIDEO_ID}_full.txt")

print("=" * 60)
print("  抖音视频深度解析 v2.0 (含OCR)")
print("=" * 60)

# ── Step 1: API + Metadata ─────────────────────────────────
print("\n[1/5] 提取元数据...")
api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={VIDEO_ID}&aid=6383"
resp = requests.get(api_url, headers=HEADERS, timeout=15)
data = resp.json()
detail = data["aweme_detail"]
video_info = detail["video"]
author = detail.get("author", {})
stats = detail.get("statistics", {})

metadata = {
    "视频ID": VIDEO_ID,
    "标题": detail.get("desc", ""),
    "作者": author.get("nickname", ""),
    "作者ID": author.get("unique_id", ""),
    "话题": [t.get("hashtag_name") or t.get("title", "") for t in detail.get("text_extra", []) if t.get("hashtag_name")],
    "时长(秒)": detail.get("duration", 0) // 1000,
    "点赞": stats.get("digg_count", 0),
    "评论": stats.get("comment_count", 0),
    "收藏": stats.get("collect_count", 0),
    "分享": stats.get("share_count", 0),
}
print(f"  标题: {metadata['标题']}")
print(f"  作者: {metadata['作者']} (@{metadata['作者ID']})")
print(f"  话题: {', '.join(metadata['话题'])}")
print(f"  时长: {metadata['时长(秒)']}s | likes={metadata['点赞']} comments={metadata['评论']} collects={metadata['收藏']}")

# ── Step 2: Download ───────────────────────────────────────
print("\n[2/5] 下载视频...")
if not os.path.exists(video_path):
    if "bit_rate" in video_info and video_info["bit_rate"]:
        best = max(video_info["bit_rate"], key=lambda x: x.get("bit_rate", 0))
        video_url = best["play_addr"]["url_list"][0]
    else:
        video_url = video_info["play_addr"]["url_list"][0]
    resp = requests.get(video_url, headers=HEADERS, stream=True, timeout=120)
    with open(video_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  已保存 ({os.path.getsize(video_path)//1024//1024}MB)")
else:
    print(f"  已存在，跳过 ({os.path.getsize(video_path)//1024//1024}MB)")

# ── Step 3: OCR on key frames ──────────────────────────────
print("\n[3/5] 提取关键帧 + OCR文字识别...")

# Get video duration via ffprobe
probe = subprocess.run([ffmpeg, '-i', video_path], capture_output=True, text=True)
dur_match = re.search(r'Duration: (\d+):(\d+):(\d+)\.(\d+)', probe.stderr)
total_sec = 0
if dur_match:
    h, m, s = map(int, dur_match.groups()[:3])
    total_sec = h * 3600 + m * 60 + s

# Extract frames: every 8 seconds (skip first 3s intro), cap at video duration
frame_interval = 8
intervals = list(range(3, min(total_sec, 120), frame_interval))
ocr_results = []

for t in intervals:
    frame_path = os.path.join(FRAMES_DIR, f"frame_{t:04d}s.png")
    subprocess.run(
        [ffmpeg, '-ss', str(t), '-i', video_path, '-vframes', '1', '-q:v', '2', frame_path, '-y'],
        capture_output=True
    )
    if os.path.exists(frame_path) and os.path.getsize(frame_path) > 1000:
        img = Image.open(frame_path)
        # OCR with Chinese + English
        try:
            text = pytesseract.image_to_string(img, lang='chi_sim+eng').strip()
            # Filter out noise (single chars, pure numbers, too short)
            if text and len(text) > 2:
                # Clean up common OCR noise
                text = re.sub(r'\s+', ' ', text)
                ocr_results.append((t, text))
        except Exception as e:
            print(f"  OCR error at {t}s: {e}")

# Deduplicate by content similarity
unique_ocr = []
seen_content = set()
for t, text in ocr_results:
    # Normalize for dedup
    key = re.sub(r'\s+', '', text)[:20]
    if key and key not in seen_content:
        seen_content.add(key)
        unique_ocr.append((t, text))

print(f"  提取了 {len(intervals)} 帧，检测到 {len(unique_ocr)} 段画面文字")

# ── Step 4: Whisper ────────────────────────────────────────
print("\n[4/5] 语音转文字...")
if not os.path.exists(audio_path):
    subprocess.run(
        [ffmpeg, '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path, '-y'],
        capture_output=True
    )

_orig = subprocess.run
def _patched(cmd_args, **kw):
    if isinstance(cmd_args, list) and cmd_args[0] == 'ffmpeg':
        cmd_args = [ffmpeg] + cmd_args[1:]
    return _orig(cmd_args, **kw)
subprocess.run = _patched

def load_audio(file_path, sr=16000):
    proc = subprocess.Popen(
        [ffmpeg, '-i', file_path, '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', str(sr), '-ac', '1', '-'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    out, _ = proc.communicate()
    return np.frombuffer(out, np.int16).astype(np.float32) / 32768.0

import whisper
whisper.audio.load_audio = load_audio
model = whisper.load_model("small")
result = model.transcribe(audio_path, language="zh")
transcript = result["text"]

# ── Step 5: Save full report ───────────────────────────────
print("\n[5/5] 保存完整报告...")
with open(full_path, 'w', encoding='utf-8') as f:
    f.write("=" * 50 + "\n")
    f.write("  抖音视频深度解析报告 (含OCR)\n")
    f.write("=" * 50 + "\n\n")

    f.write("【元数据】\n")
    for k, v in metadata.items():
        f.write(f"  {k}: {v}\n")

    f.write("\n【画面OCR文字】\n")
    if unique_ocr:
        for t, text in unique_ocr:
            f.write(f"  [{t}s] {text}\n")
    else:
        f.write("  (未检测到画面文字)\n")

    f.write("\n【语音字幕全文】\n")
    f.write(transcript + "\n")

print("\n[OK] 完成!")
print(f"  报告: {full_path}")

if unique_ocr:
    print(f"\n--- OCR检测到的画面文字 ---")
    for t, text in unique_ocr:
        print(f"  [{t}s] {text}")
else:
    print(f"\n  (画面中未检测到文字)")

print(f"\n--- 语音字幕(前300字) ---")
print(transcript[:300] + "...")
