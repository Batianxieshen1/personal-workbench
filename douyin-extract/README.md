# 🎬 douyin-extract

> **把 60 秒的视频，变成 5 秒就能读完的文字档案。**
> 一条命令，提取抖音视频的元数据、画面文字、语音字幕——让每一条视频都变成可搜索、可引用、可归档的知识资料。

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![ASR](https://img.shields.io/badge/%E8%AF%AD%E9%9F%B3%E8%AF%86%E5%88%AB-OpenAI%20Whisper-orange)
![OCR](https://img.shields.io/badge/%E7%94%BB%E9%9D%A2%E6%96%87%E5%AD%97-Tesseract%20OCR-green)
![License](https://img.shields.io/badge/license-MIT-green)
![AI Skill](https://img.shields.io/badge/AI%20Skill-%E5%BC%80%E7%AE%B1%E5%8D%B3%E7%94%A8-8A2BE2)

---

## 这是什么？

刷到一条干货视频，想记笔记却只能一遍遍暂停？想引用博主的论证，却只能手动逐字抄写？

**douyin-extract** 是一个开箱即用的抖音视频深度解析工具。给它一个链接，它会自动完成一条完整的四步流水线：

```
📋 元数据提取 → ⬇️ 视频下载 → 🔍 画面OCR（可选） → 🎙️ Whisper 语音转文字 → 📄 深度解析报告
```

最终产出一份结构化报告：**标题、作者、点赞收藏数据、画面里的每一行字、口播的每一个字**，全部落盘为纯文本，随便搜索、随便引用。

它既可以作为**命令行工具**独立使用，也可以作为 **AI Skill** 安装进 Claude Code / ZCode 等 Agent 环境——装好之后，你只需要对着 AI 说一句"提取这个抖音视频的内容"，剩下的全自动。

## ✨ 核心特性

| 特性 | 说明 |
|---|---|
| 🔗 **输入零门槛** | 裸视频 ID、`www.douyin.com/video/xxx` 完整链接、`v.douyin.com` 分享短链，通吃 |
| 🧠 **双层内容提取** | Whisper 转写"说出来的话"，Tesseract OCR 识别"画面上的字"，音画内容一个不漏 |
| 📦 **智能缓存** | 视频、音频、报告按视频 ID 落盘，重复解析自动跳过已完成的步骤，增量运行 |
| 🤖 **AI Skill 原生** | 自带 SKILL.md，复制进 Agent 的 skills 目录即可被 AI 自动发现和调用 |
| 🔧 **零外部依赖安装** | ffmpeg 由 `imageio-ffmpeg` 自动携带，无需手动配置环境 |
| 📊 **双输出格式** | 人类可读的 Markdown 风格报告 + 机器可解析的 JSON，程序化处理无障碍 |
| ⚙️ **全路径可配置** | Cookie、输出目录、OCR 组件全部支持环境变量覆盖，可移植到任何机器 |
| 📓 **Obsidian 自动归档** | 解析报告一键转为标准笔记（YAML frontmatter + 索引 + 视频ID去重），dry-run 预览、确认后写入 |

## 🎯 效果展示

```console
$ python douyin_extract.py https://www.douyin.com/video/7669746385536765211

============================================================
  抖音视频深度解析 v3.1
============================================================

[1/4] 提取元数据...
  标题: 假如你从8月3号开始转AI产品岗，到底多久能拿下？ #AI产品经理 #程序员 ...
  作者: 懂点Ai的阿哲 (@57489472278)
  时长: 53s | likes=153 comments=58 collects=142

[2/4] 下载视频...
  已保存 (8MB)

[3/4] 跳过OCR (口播/真人出镜类视频按需开启)

[3/4] 语音转文字...

[OK] 报告已保存: douyin_output/7669746385536765211_full.txt
```

53 秒的视频，不到一分钟，一份包含**元数据 + 全文字幕**的解析报告就躺在了你的输出目录里。

## 🚀 快速开始

### 1️⃣ 环境要求

| 依赖 | 版本要求 | 用途 |
|---|---|---|
| Python | 3.10+ | 运行环境 |
| ffmpeg | 不需要手动装 | `imageio-ffmpeg` 自动携带 |
| Tesseract-OCR | 可选 | 仅 `--ocr` 模式需要（[下载地址](https://github.com/UB-Mannheim/tesseract/wiki)），并需安装中文包 `chi_sim` |

### 2️⃣ 安装依赖

```bash
git clone https://github.com/Batianxieshen1/personal-workbench.git
cd personal-workbench/douyin-extract
pip install requests imageio-ffmpeg numpy openai-whisper
# 需要画面 OCR 时额外安装：
pip install pytesseract Pillow
```

> 💡 Whisper 首次运行会自动下载 `small` 模型（约 460MB），下载一次后永久缓存，之后离线可用。

### 3️⃣ 配置 Cookie（一次性）

脚本通过抖音网页版 API 获取数据，需要登录态 Cookie：

1. 浏览器打开 [douyin.com](https://www.douyin.com) 并登录
2. 按 `F12` 打开开发者工具 → 切到 **Network** 标签 → 刷新页面
3. 在搜索框输入 `aweme`，点开任意一个请求
4. 在 **Request Headers** 里复制完整的 `Cookie` 值
5. 保存到脚本同目录，命名为 `.douyin_cookie`（一行纯文本）：

```bash
echo "粘贴你的Cookie" > .douyin_cookie
```

> ⏳ Cookie 有效期约 60 天。过期后脚本会明确报错提示，重新抓一次覆盖即可。

### 4️⃣ 运行第一条命令

```bash
python scripts/douyin_extract.py https://v.douyin.com/xxxxxx/
```

完成。去 `douyin_output/` 目录查看你的第一份解析报告。

## 📖 完整用法

### 命令格式

```bash
python scripts/douyin_extract.py <视频ID或链接> [--ocr] [--output-dir 目录] [--cookie "字符串"]
```

| 参数 | 说明 |
|---|---|
| `<视频ID或链接>` | 支持三种形式：`7669746385536765211` / `https://www.douyin.com/video/xxx` / `https://v.douyin.com/xxx` |
| `--ocr` | 开启画面文字识别。**字幕型/教程型/图文型视频建议开启**；纯口播视频可省略，速度更快 |
| `--output-dir` | 指定输出目录，默认为当前目录下的 `douyin_output/` |
| `--cookie` | 临时手动指定 Cookie（优先级最高） |

### 环境变量

不想把配置写死在命令里？全部支持环境变量：

| 环境变量 | 作用 | 默认值 |
|---|---|---|
| `DOUYIN_COOKIE` | 登录态 Cookie | 无 |
| `DOUYIN_COOKIE_FILE` | Cookie 文件路径 | `./.douyin_cookie`，回退到 `~/Desktop/agent/.douyin_cookie` |
| `DOUYIN_TESSERACT` | Tesseract 可执行文件路径 | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `DOUYIN_TESSDATA` | Tesseract 语言包目录 | `~/tessdata` |
| `DOUYIN_OCR_LANG` | OCR 识别语言 | `chi_sim+eng` |

Cookie 查找优先级：`--cookie` 参数 → `DOUYIN_COOKIE` 环境变量 → 当前目录 `.douyin_cookie` → 回退路径。

### 输出文件

```
douyin_output/
├── <视频ID>.mp4        # 视频原片（最高画质码率）
├── <视频ID>.wav        # 16kHz 单声道音频（转写用中间产物）
└── <视频ID>_full.txt   # ⭐ 深度解析报告（核心产物）
```

报告结构：

```
==================================================
  抖音视频深度解析报告
==================================================

【元数据】        标题 / 作者 / 话题 / 时长 / 点赞 / 评论 / 收藏 / 分享
【画面OCR文字】   [时间戳] 逐帧识别的画面文字（开启 --ocr 时）
【语音字幕全文】  Whisper 完整转写文本
```

## 📓 Obsidian 知识库归档

解析报告可以直接转成标准 Obsidian 笔记，沉淀进你的知识库：

```bash
# 预览模式：生成笔记内容但不写入（确认制）
python scripts/report_to_note.py <报告路径或视频ID> --dry-run

# 确认无误后正式写入 + 更新索引
python scripts/report_to_note.py <报告路径或视频ID>
```

**脚本做了什么**：

- 在知识库中创建 `07-抖音视频/`，每条视频一篇笔记，frontmatter 包含 `tags / source / date / 视频ID / 点赞 / 评论 / 收藏 / 分享` 等字段（可配合 Dataview 做视频数据看板）
- 自动生成并维护 `抖音视频索引.md` 汇总表格
- 按 **视频 ID 去重**：重复归档自动跳过，`--force` 覆盖
- `--summary` / `--transcript` 可注入 AI 整理的「核心要点」和断句版字幕，原始转写折叠保留

知识库路径优先级：`--vault` 参数 > `DOUYIN_VAULT_DIR` 环境变量 > `~/Desktop/agent/我的知识库`。

> 💡 **搭配 AI Agent 使用体验最佳**：让 AI 通读字幕后撰写要点、整理断句字幕，dry-run 预览给你确认，确认后自动入库——你只负责说"可以"。

## 🤖 作为 AI Skill 使用（推荐）

这是本工具**最有价值的打开方式**。它自带符合 [Agent Skills 规范](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) 的 `SKILL.md`，装进 AI Agent 后，你不需要记任何命令——

### 安装

```bash
# Claude Code 用户
git clone https://github.com/Batianxieshen1/personal-workbench.git
mkdir -p ~/.claude/skills
cp -r personal-workbench/douyin-extract ~/.claude/skills/

# ZCode 用户
cp -r personal-workbench/douyin-extract ~/.zcode/skills/
```

### 使用

重启会话后，直接用自然语言对话：

> 🗣️ 「帮我提取这个抖音视频的内容：https://v.douyin.com/xxxxxx/」
> 🗣️ 「把这条视频转成文字笔记，顺便总结成三个要点」
> 🗣️ 「这是个字幕教程视频，连画面里的代码一起提取出来」

AI 会自动定位到这个 Skill，解析链接、跑流水线、读取报告，然后**直接把整理好的内容回答给你**——提取和消化一步到位。

## 💡 实用场景

- 📚 **知识管理**：知识区博主的干货视频批量转文字，喂进笔记软件建立个人知识库，从此搜索"那天刷到的那个视频"变成搜索关键词
- ✍️ **内容创作**：拆解爆款视频的完整文案结构——钩子、节奏、关键词密度，像素级学习对标账号
- 🔍 **竞品调研**：元数据（点赞/评论/收藏比）一键落表，配合脚本批量分析赛道数据
- 🌐 **无障碍阅读**：为听障朋友或不方便外放的场合提供完整字幕，信息获取不再受限于声音
- 📝 **课堂/讲座归档**：讲座类长视频转写后按时间戳整理，复习时直接读文字

## ❓ 常见问题

<details>
<summary><b>报错 <code>API返回异常，请检查Cookie是否过期</code></b></summary>

Cookie 失效了。按[快速开始第 3 步](#3️⃣-配置-cookie一次性)重新抓取，覆盖 `.douyin_cookie` 文件即可。
</details>

<details>
<summary><b>首次运行很慢，卡在下载模型？</b></summary>

Whisper `small` 模型约 460MB，仅在首次运行时下载一次。耐心等待即可，后续运行直接加载本地缓存。
</details>

<details>
<summary><b>转写结果里有错别字？</b></summary>

Whisper 对专有名词、品牌名的识别偶有偏差，属于开源语音识别的正常水平。可将 `small` 换成 `medium`/`large` 模型（修改脚本中 `whisper.load_model("small")`）换取更高准确率，代价是更慢的速度。
</details>

<details>
<summary><b>CPU 转写太慢怎么办？</b></summary>

53 秒视频约需 1 分钟。长视频建议挂后台运行；有 NVIDIA 显卡的话安装 CUDA 版 PyTorch 可提速 5-10 倍。
</details>

<details>
<summary><b>会被抖音风控吗？</b></summary>

脚本使用网页版同款 API 与真实登录态，单次使用与正常浏览行为无异。请勿高频批量请求（建议间隔数秒），既是对平台友好，也是保护你自己的账号。
</details>

## ⚠️ 免责声明

本项目仅供**个人学习与研究**使用。请尊重视频作者的著作权，提取的内容请勿用于商业用途或二次分发；请遵守抖音平台的服务条款，合理控制请求频率。因使用本项目产生的任何问题由使用者自行承担。

## 📄 License

[MIT](./LICENSE) © 2026 Batianxieshen1

---

<div align="center">

**如果这个工具帮你省下了抄字幕的时间，点个 ⭐ 就是最好的鼓励！**

</div>
