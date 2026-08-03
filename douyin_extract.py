import requests
import re
import json
import subprocess
import sys
import os
import imageio_ffmpeg
import numpy as np

VIDEO_ID = "7656065001418404723"
COOKIE = "bd_ticket_guard_client_web_domain=2; uid_tt=5c76092ee50c0843e5a7e418d9d82cdb; uid_tt_ss=5c76092ee50c0843e5a7e418d9d82cdb; sid_tt=0057c7cec80cc44503ae3397d59423b4; sessionid=0057c7cec80cc44503ae3397d59423b4; sessionid_ss=0057c7cec80cc44503ae3397d59423b4; is_staff_user=false; _bd_ticket_crypt_cookie=35dd845c945e5f5e6f83d68c5f2f57d2; live_use_vvc=%22false%22; hevc_supported=true; enter_pc_once=1; SEARCH_RESULT_LIST_TYPE=%22single%22; xgplayer_user_id=99517796221; UIFID_TEMP=834e8292a57169584b829a284cfad93df7bd06dccdbce3984f79b694b3d0c587fab7082bf3e25e7b92b1af849dea5b4868cdcc55557bafa3b29fc5cb215827f603697e9fb97afda0dcbea2019310e6ad21a80c2c46cd5d4d9c7f4212b8b47130; fpk1=U2FsdGVkX1+ZQdATLrM3wUm8xbIXjcRw3WNUPTgw0rFIxZp3MqI8dfILLiJe6MXHGiA3//0Q8+paTrhp23XWCA==; fpk2=9be3e00191ffcce29a6799859112a898; UIFID=834e8292a57169584b829a284cfad93df7bd06dccdbce3984f79b694b3d0c587fab7082bf3e25e7b92b1af849dea5b4868cdcc55557bafa3b29fc5cb215827f674d172838cd0ae181f123344c008e90109685bb34731f9f503e730e60d7fb4ef0a5526511e8c01b8010689a17393f7433561f7f9ab2adbfcc1db152b8045082b9a419d0904bd4c5213aff80dba30d6e157958e2e6de2cb7bff9dd289353c288a56661076106f1988a727e20fad983b20; UIFID=834e8292a57169584b829a284cfad93df7bd06dccdbce3984f79b694b3d0c587fab7082bf3e25e7b92b1af849dea5b4868cdcc55557bafa3b29fc5cb215827f674d172838cd0ae181f123344c008e90109685bb34731f9f503e730e60d7fb4ef0a5526511e8c01b8010689a17393f7433561f7f9ab2adbfcc1db152b8045082b9a419d0904bd4c5213aff80dba30d6e157958e2e6de2cb7bff9dd289353c288a4572420f3f4374d41576486a4f786d1bb9692c416e7d37ab7cd1a1cf2f11b34e; __itrace_wid=38210d21-8183-46b6-874b-43f773623c69; xgplayer_device_id=55972314661; my_rd=2; is_dash_user=1; has_biz_token=false; live_private_user=0; sid_guard=0057c7cec80cc44503ae3397d59423b4%7C1783328095%7C5184000%7CFri%2C+04-Sep-2026+08%3A54%3A55+GMT; session_tlb_tag=sttt%7C14%7CAFfHzsgMxEUDrjOX1ZQjtP_________nASbcki3dNEDH9YE8_dRzwr4lel878_BO-x0ds15CsM0%3D; sid_ucp_v1=1.0.0-KGNlOGQ1MTdlNmZhNzZjOGVkYTc0NDUwZjAwM2NmMWQ5ODUwYTdkMGIKGQjI5Ku07QIQ39qt0gYY7zEgDDgGQPQHSAQaAmhsIiAwMDU3YzdjZWM4MGNjNDQ1MDNhZTMzOTdkNTk0MjNiNA; ssid_ucp_v1=1.0.0-KGNlOGQ1MTdlNmZhNzZjOGVkYTc0NDUwZjAwM2NmMWQ5ODUwYTdkMGIKGQjI5Ku07QIQ39qt0gYY7zEgDDgGQPQHSAQaAmhsIiAwMDU3YzdjZWM4MGNjNDQ1MDNhZTMzOTdkNTk0MjNiNA; s_v_web_id=verify_mrsuwl9m_CrjYE8pE_d8wQ_4ixl_Au9s_KoGF56EubjNL; passport_csrf_token=5d7ff41b0ef196a8e5c1a5401f3d6bbd; passport_csrf_token_default=5d7ff41b0ef196a8e5c1a5401f3d6bbd; bd_ticket_guard_ts_sign_id=6d48eb3d1f13f725a800; passport_auth_mix_state=a7yjs5uxuflnaxhmfrj7cqqfoa74x0y2; odin_tt=b58736e15a226cad084cde8b67696a4db81b0fcea1900b0fd4cec921f6d482e3df299807575a90359251c9d3ef574215da52fc54daa8daab78c027902332f5d8; ttwid=1%7C85c-HmAcGKLIsHqYlwWen8XZ-wHJknPPQHSFTDzS-SY%7C1785340847%7C9d00d108c8dfe8d964bcb7d09d1e76814156530d252bb103d5f3966f4d272192; IsDouyinActive=true"

OUTPUT_DIR = "douyin_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Cookie": COOKIE,
}

# Step 1: Get video URL from Douyin API
print("[1/4] 调用抖音API获取视频链接...")
api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={VIDEO_ID}&aid=6383"
resp = requests.get(api_url, headers=HEADERS, timeout=15)

try:
    data = resp.json()
except:
    print(f"API返回非JSON: {resp.text[:200]}")
    sys.exit(1)

if "aweme_detail" not in data:
    print(f"API返回异常: {json.dumps(data, ensure_ascii=False)[:300]}")
    sys.exit(1)

video_info = data["aweme_detail"]["video"]
video_url = None

# Try bit_rate first (highest quality)
if "bit_rate" in video_info and video_info["bit_rate"]:
    best = max(video_info["bit_rate"], key=lambda x: x.get("bit_rate", 0))
    if "play_addr" in best:
        video_url = best["play_addr"]["url_list"][0]
elif "play_addr" in video_info:
    video_url = video_info["play_addr"]["url_list"][0]

if not video_url:
    print("无法从API响应中提取视频链接")
    sys.exit(1)

print(f"视频链接获取成功")

# Also get video description
desc = data["aweme_detail"].get("desc", "")
print(f"视频标题: {desc}")

# Step 2: Download video
print("[2/4] 下载视频...")
video_path = os.path.join(OUTPUT_DIR, f"{VIDEO_ID}.mp4")

resp = requests.get(video_url, headers=HEADERS, stream=True, timeout=120)
total = int(resp.headers.get('content-length', 0))
downloaded = 0
with open(video_path, 'wb') as f:
    for chunk in resp.iter_content(chunk_size=8192):
        f.write(chunk)
        downloaded += len(chunk)
        if total:
            pct = downloaded * 100 // total
            print(f"\r  下载中... {pct}% ({downloaded//1024//1024}MB/{total//1024//1024}MB)", end='')
print(f"\n  视频已保存: {video_path}")

# Step 3: Extract audio
print("[3/4] 提取音频...")
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
audio_path = os.path.join(OUTPUT_DIR, f"{VIDEO_ID}.wav")
result = subprocess.run(
    [ffmpeg, '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path, '-y'],
    capture_output=True
)
print(f"  音频已提取: {audio_path}")

# Step 4: Whisper transcription
print("[4/4] Whisper 语音转文字...")

_original_run = subprocess.run
def _patched_run(cmd_args, **kwargs):
    if isinstance(cmd_args, list) and cmd_args[0] == 'ffmpeg':
        cmd_args = [ffmpeg] + cmd_args[1:]
    return _original_run(cmd_args, **kwargs)
subprocess.run = _patched_run

def load_audio_manual(file_path, sr=16000):
    cmd = [ffmpeg, '-i', file_path, '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', str(sr), '-ac', '1', '-']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    out, _ = proc.communicate()
    return np.frombuffer(out, np.int16).astype(np.float32) / 32768.0

import whisper
whisper.audio.load_audio = load_audio_manual

print("  加载Whisper small模型...")
model = whisper.load_model("small")
print("  开始转录...")
result = model.transcribe(audio_path, language="zh")

# Save output
txt_path = os.path.join(OUTPUT_DIR, f"{VIDEO_ID}.txt")
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write(f"标题: {desc}\n\n")
    f.write(result["text"])

print(f"\n完成! 字幕已保存到: {txt_path}")
print(f"\n=== 字幕内容 ===")
print(result["text"])
print(f"================")
