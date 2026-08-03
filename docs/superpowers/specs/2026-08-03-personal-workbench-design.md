# 个人工作台（Personal Workbench）设计方案

- 日期：2026-08-03
- 状态：已获用户批准（2026-08-03）
- 定位：信息聚合大屏 ——「一天一屏看全局」

## 1. 背景与目标

用户是学生，日常高频使用：Obsidian 知识库（日记/工作/AI产品/Agent开发分区）、大模型备考体系（`study_progress.md` + `references/quiz_bank.json`）、抖音视频提取脚本（`douyin_extract_v3.py`）。网上"个人工作台"很火，用户想要一套属于自己的本地工作台，把日常信息聚合到一屏，减少在多个软件间来回切换。

核心目标：**打开即见全局** —— 学习进度、今日计划、天气时钟、雅思、灵感、复盘入口，一屏呈现。

## 2. 模块清单（9 个）

| # | 模块 | 说明 |
| --- | --- | --- |
| 1 | 学习进度 | 大模型课程 ch1-ch5 进度、备考计划状态（实时读取 `study_progress.md`） |
| 2 | 今日计划 | 每日任务清单，支持勾选完成（原"今日待办"改名） |
| 3 | 日记/笔记入口 | 一键打开/新建 Obsidian 日记，知识库快捷跳转 |
| 4 | 天气 + 时钟 | 时间感 + 生活感 |
| 5 | 快捷工具 | 抖音提取脚本、题库测验等小工具启动入口 |
| 6 | 资源/链接收藏 | 常用网站、参考资料卡片墙 |
| 7 | 雅思英语 | 每日任务 + 进度看板 + 生词本（艾宾浩斯复习） |
| 8 | 选题灵感 | AI 每天自动生成新奇点子，用户筛选保留（DeepSeek） |
| 9 | 内容复盘 | 每日总结 + 内容复盘 + 周报（三层） |

## 3. 技术方案（用户已选 B：本地轻量服务器）

| 层 | 选型 | 理由 |
| --- | --- | --- |
| 后端 | Python 3.13 + FastAPI + uvicorn | AI 行业事实标准，自带交互式 API 文档（/docs），贴合用户学习方向 |
| 前端 | 原生 HTML/CSS/JS 单页应用（无构建步骤） | 零 npm 依赖、好改好懂；护眼暖调主题用 CSS 变量实现 |
| 存储 | `data/` 目录下 JSON 文件 | 人类可读、可 git、与用户 md 文件习惯一致 |
| AI | DeepSeek API（OpenAI 兼容接口） | 国产便宜，一次生成几分钱；密钥存 `.env`，仅服务端调用 |
| 天气 | Open-Meteo API | 免费、无需注册 key，服务端代理解决跨域 |
| 运行 | `python run.py` 一键启动 + 自动开浏览器；配套 `start.bat` | Windows 双击即用 |

### 数据文件规划（`data/` 目录）

- `data/plans/YYYY-MM-DD.json` — 每日计划（按天分文件）
- `data/ideas.json` — 灵感池（日期、来源 AI/manual、状态 kept/discarded）
- `data/vocab.json` — 雅思生词（单词、释义、添加日期、下次复习日期、复习阶段）
- `data/ielts.json` — 雅思进度（目标分、四科状态、备考阶段）
- `data/reviews/YYYY-MM-DD.json` — 每日总结
- `data/content.json` — 内容复盘（灵感 → 产出状态）
- `data/weekly/YYYY-Www.json` — 周报（自动汇总 + AI 总结）
- `data/config.json` — 城市经纬度、昵称、快捷链接等
- `.env` — DEEPSEEK_API_KEY（不进 git）

### 艾宾浩斯复习节奏

生词复习间隔：第 1 / 3 / 7 / 14 / 30 天，到期的词出现在"今日复习队列"。

## 4. 页面结构（布局 = 方案 A 侧边栏 + 方案 C 信息大屏的结合体）

- 左侧窄导航：首页 / 学习 / 雅思 / 灵感 / 复盘 / 工具
- **首页（默认）**：时钟+天气、今日计划（可勾选）、学习进度、雅思速览、今日灵感、复盘入口 —— 一屏网格
- **学习页**：大模型课程进度详情、备考计划、错题本链接（Obsidian）
- **雅思页**：进度看板、今日任务、生词本（复习队列）
- **灵感页**：今日 AI 批次 + 手动添加 + 收藏管理
- **复盘页**：每日总结（AI 起草）、内容复盘、周报
- **工具页**：抖音提取、Obsidian 跳转、链接收藏墙

### 视觉风格（用户已选）

**护眼暖调**：米黄纸感背景 + 木质暖色强调（卡片 #faf4e6 系、强调 #c9a35f），CSS 变量集中管理主题色。

## 5. API 设计（前缀 `/api`）

| 端点 | 作用 |
| --- | --- |
| `GET /api/overview` | 首页聚合：计划+进度+天气+雅思+今日灵感+复习提醒，一次拿全 |
| `GET /api/plan?date=` / `POST` / `PATCH` | 今日计划增删勾选 |
| `GET /api/ideas` / `POST /api/ideas` / `POST /api/ideas/generate` / `PATCH /api/ideas/:id` | 灵感池管理 + 触发 AI 生成 |
| `GET /api/vocab` / `POST /api/vocab` / `PATCH /api/vocab/:id/review` / `DELETE` | 生词本 + 复习打卡（推进阶段） |
| `GET /api/ielts` / `PATCH /api/ielts` | 雅思进度 |
| `GET /api/reviews?date=` / `POST /api/reviews` / `POST /api/reviews/ai-draft` | 每日总结 + AI 起草 |
| `GET /api/weekly?week=` | 周报（聚合 + AI 总结） |
| `GET /api/progress` | 解析 `study_progress.md` 章节完成状态 |
| `GET /api/weather` | 天气代理（Open-Meteo） |
| `POST /api/tools/douyin` + `GET /api/tools/douyin/:job` | 抖音提取异步任务（任务 ID + 状态轮询） |
| `GET /api/config` / `PATCH /api/config` | 设置：城市、昵称、快捷链接 |

## 6. 关键设计决策

1. **灵感懒加载**：当天首次打开首页时若今日批次不存在，自动调用 DeepSeek 生成 5 条新奇点子；用户可"换一批"/手动添加/收藏/丢弃。避免定时任务复杂度。
2. **AI 降级**：DeepSeek 无 key / 调用失败时，灵感与复盘模块自动降级为手动录入，其余模块不受影响。
3. **单卡容错**：前端每个卡片独立 fetch、独立渲染，坏一个不影响整页；天气失败显示 "—"。
4. **抖音提取走异步**：`POST /api/tools/douyin` 立即返回 job_id，后端后台线程跑 `python douyin_extract_v3.py <video_id>`（脚本接受 video_id；前端输入分享链接时后端解析出 ID），前端轮询进度，完成后展示报告摘要（元数据 + OCR 数 + 字幕长度 + 报告路径）。
5. **Obsidian 联动**：用 `obsidian://open?vault=我的知识库&file=01-日记/YYYY-MM-DD` URI 一键打开/新建日记，无需插件。

## 7. 容错与错误处理

- AI 失败 → 降级手动，提示"API 不可用"，不抛错阻塞
- 天气失败 → 显示 "—"
- 抖音任务超时 → 友好报错 + 可取消
- `study_progress.md` 读取失败 → 显示"进度文件未找到"占位卡

## 8. 测试策略

- 后端核心纯逻辑用 pytest：计划 CRUD、艾宾浩斯复习日期计算、md 进度解析、灵感生成降级路径
- 前端手工走查：各卡片加载、勾选交互、工具页异步任务
- 不追求覆盖率，聚焦纯函数与降级路径

## 9. 实施里程碑

- **M1 骨架**：FastAPI + 静态前端 + 侧边栏 + 首页网格 + 今日计划 + 时钟天气
- **M2 数据闭环**：学习进度读取 + 雅思三件套 + 生词本复习算法
- **M3 AI 能力**：DeepSeek 接入 + 灵感懒加载 + AI 起草复盘 + 周报
- **M4 集成**：抖音异步任务 + Obsidian 联动 + 设置页 + 护眼暖调打磨

## 10. 开放问题（后续可讨论）

- 雅思进度看板的数据来源：手动维护 vs 后续对接真题数据
- 资源收藏是否需要导入/导出（与 Obsidian 双向）
- 抖音脚本 OCR 默认关闭（耗时），工具页是否提供开关
- 是否引入 git 管理整个项目（当前目录无 git 仓库）
