# 个人工作台（Personal Workbench）

本地运行的「一天一屏」信息聚合工作台：AI 行动指南、今日计划、学习备考、雅思、灵感、复盘、统计、资讯、基金，中英双语 + 夜间模式。

## 快速开始

```bash
cd workbench
pip install -r requirements.txt   # 首次
python run.py                     # 启动并自动打开浏览器
```

Windows 也可以直接双击 `start.bat`。

- 服务地址：http://127.0.0.1:8765（局域网：http://<本机IP>:8765，手机同 WiFi 可访问）
- API 文档：http://127.0.0.1:8765/docs
- `run.py` 特性：端口自愈（自动清理旧进程）、每天首次启动自动备份数据

## 功能一览

| 板块 | 功能 |
| --- | --- |
| 🗺 今日行动 | AI 晨间导航（打字机）+ 优先级行动清单 + 浏览器提醒 |
| 📋 今日计划 | 星标重要度 / 双击编辑 / 完成时间记录 / 一键雅思任务模板 |
| 📚 学习 | study_progress.md 实时解析 + 阶段勾选写回 + 番茄钟 + 备考计划 |
| 🎯 雅思 | 进度看板（可编辑）/ 生词本（艾宾浩斯 + 翻转卡 + 认识/不认识判定） |
| 💡 灵感 | AI 每天 5 条 + 最佳推荐 + 备注 + 收藏/丢弃/采用 |
| 📝 复盘 | 每日总结 AI 起草 + 周报 + 内容复盘（产出追踪）+ Obsidian 同步 |
| 📊 统计 | 连续天数 / 周完成率 / 生词统计 / 灵感采用率 / 7 天趋势图 |
| 📰 资讯 | AI 最新（aihot 官方 API）+ 国内（百度热搜/IT之家/B站）+ 国外（BBC/HN/TechCrunch），1 小时缓存 + 手动刷新 |
| 💰 基金 | 关注列表涨跌排行（红涨绿跌）+ 30 天走势图 + 工具页管理（天天基金数据源） |
| 🛠 工具 | 抖音提取异步任务 / Obsidian 联动 / 资源收藏 / 数据导出 |

**其他**：中英双语切换（设置页）、🌙 夜间模式、毛玻璃/Spotlight/全套动效、PWA（localhost 可添加主屏幕）、`python backup.py` 手动备份。

## 测试

```bash
cd workbench
python -m pytest tests -v
```

## 目录结构

```
workbench/
  app/       后端（FastAPI）17 个模块：storage/plan/weather/config/progress/ielts/vocab/
            deepseek/ideas/reviews/links/tools/obsidian/guide/stats/news/funds
  static/    前端（原生 HTML/CSS/JS + i18n 中英字典）
  data/      数据（JSON，git 忽略）
  tests/     pytest 测试（134 个）
  run.py     一键启动（端口自愈 + 自动备份）
```

## 里程碑

- [x] M1 骨架：今日计划 + 时钟天气 + 侧边栏导航（2026-08-03）
- [x] M2 数据闭环：学习进度 + 雅思三件套 + 生词本艾宾浩斯（2026-08-03）
- [x] M3 AI 能力：DeepSeek 灵感 + AI 起草复盘 + 周报（2026-08-03）
- [x] M4 集成：抖音异步 + Obsidian 联动 + 设置页（2026-08-03）
- [x] 深化：统计页 / 内容复盘 / 任务模板 / 双语 / 夜间模式 / 动效（2026-08-04）
- [x] 资讯 + 基金板块（2026-08-08）
- 🎉 **全部完成**

设计文档：`docs/superpowers/specs/2026-08-03-personal-workbench-design.md`
