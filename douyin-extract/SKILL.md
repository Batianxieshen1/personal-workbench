---
name: douyin-extract
description: "提取抖音视频的完整内容：元数据（标题/作者/数据）、画面OCR文字、Whisper 语音转文字，并生成深度解析报告。接受视频ID或任何链接（含 v.douyin.com 分享短链）。当用户提到抖音视频提取、抖音转文字、抖音字幕、抖音视频内容总结、下载抖音视频、解析抖音链接、douyin video、tiktok 抖音，或者粘贴任何 douyin.com / v.douyin.com 链接并想了解视频内容时，务必使用此技能——即使用户没有明说'提取'，只要意图是获取某个抖音视频里的信息，都应该用它。"
metadata:
  author: batianxieshen
  version: "1.0.0"
---

# 抖音视频深度解析 (douyin-extract)

把一个抖音视频变成结构化文字资料。流水线四步：

```
元数据(标题/作者/点赞数) → 下载mp4 → [可选]OCR画面文字 → Whisper语音转文字 → 报告txt
```

脚本位置：`scripts/douyin_extract.py`，用绝对路径调用，与当前工作目录无关。

## 基本用法

```bash
python "<skill路径>/scripts/douyin_extract.py" <视频ID或链接> [--ocr] [--output-dir 目录]
```

- **视频ID或链接**：以下形式都直接可传，脚本会自动归一化：
  - 裸ID：`7669746385536765211`
  - 完整链接：`https://www.douyin.com/video/7669746385536765211`
  - 分享短链：`https://v.douyin.com/xxxxxx/`（自动跟随重定向解析）
  - 用户给"分享口令"文本时，先用正则从中捞出上面的链接或19位左右的长数字ID
- `--ocr`：加画面文字识别。**判断标准**：字幕/教程/图文/新闻类视频加 `--ocr`；纯口播、真人出镜说话的可以不加（OCR 每 8 秒抽一帧，耗时明显增加）。不确定时加上更稳妥，最多多花一两分钟。
- `--output-dir`：输出目录，默认为当前目录下的 `douyin_output/`。给用户干活时建议显式指定到用户的项目目录。

## 运行后必做

1. 脚本最后一行会输出 `--- JSON_OUTPUT ---` + 一行 JSON（含 metadata、ocr_count、transcript_length、report_path），解析它确认成功。
2. **读取 `report_path` 指向的报告文件**，里面有完整的元数据、OCR 文字和语音字幕全文——这才是给用户的内容来源，JSON 行里只有长度没有正文。
3. 基于报告内容回答用户的问题（总结/翻译/整理要点等），不要只把文件路径甩给用户。

## Cookie 管理（重要）

脚本需要登录态 Cookie 才能调抖音 API，按以下优先级自动查找：

1. `--cookie "<cookie_str>"` 参数
2. 环境变量 `DOUYIN_COOKIE`
3. 当前目录 `.douyin_cookie`
4. `~/Desktop/agent/.douyin_cookie`（历史缓存，通常直接命中）

**Cookie 会过期**（约 60 天有效期）。如果脚本报 `API返回异常，请检查Cookie是否过期`，按这个流程刷新：

1. 浏览器打开 douyin.com 并登录
2. F12 → Network → 刷新页面 → 搜 `aweme` → 点任意请求 → 复制请求头里完整的 Cookie 值
3. 覆盖写入 `~/Desktop/agent/.douyin_cookie`（一行纯文本）

Cookie 是敏感凭据，不要把它写进代码、日志或输出给用户看。

## 输出文件

输出目录下按视频ID命名：

| 文件 | 内容 |
|---|---|
| `<id>.mp4` | 视频原片 |
| `<id>.wav` | 16kHz 单声道音频（转写用） |
| `<id>_full.txt` | **深度解析报告**（元数据 + OCR文字 + 字幕全文） |

下载和转写都有文件级缓存：同 ID 重复运行会跳过已存在的 mp4/wav，只重跑必要步骤。

## 依赖

首次使用前确认（本机已装好）：

```bash
pip install requests imageio-ffmpeg numpy openai-whisper
# --ocr 才需要：
pip install pytesseract Pillow
```

- ffmpeg 由 `imageio_ffmpeg` 自带，不需要系统安装
- Whisper 首次运行会下载 `small` 模型（约 460MB），之后有缓存
- OCR 依赖本机 Tesseract：`C:\Program Files\Tesseract-OCR\tesseract.exe`，中文包在 `~/tessdata`

## 已知限制

- 需要网络与有效登录态 Cookie；API 无签名参数（a_bogus），抖音若加强风控可能需要补签名
- Whisper 转写在 CPU 上运行，长视频（>5分钟）耗时按分钟级增长
- 仅供个人学习研究使用，注意尊重视频作者的版权与隐私
