# 个人工作台（Personal Workbench）

本地运行的「一天一屏」信息聚合工作台：今日计划、时钟天气、学习进度、雅思、AI 灵感、复盘。

## 快速开始

```bash
cd workbench
pip install -r requirements.txt   # 首次
python run.py                     # 启动并自动打开浏览器
```

Windows 也可以直接双击 `start.bat`。

- 服务地址：http://127.0.0.1:8765（局域网：http://<本机IP>:8765）
- API 文档：http://127.0.0.1:8765/docs

## 测试

```bash
cd workbench
python -m pytest tests -v
```

## 目录结构

```
workbench/
  app/       后端（FastAPI）：storage / plan / weather / config / main
  static/    前端（原生 HTML/CSS/JS）：index.html / style.css / app.js
  data/      数据（JSON，git 忽略）
  tests/     pytest 测试
  run.py     一键启动
```

## 里程碑

- [x] M1 骨架：今日计划 + 时钟天气 + 侧边栏导航（2026-08-03）
- [x] M2 数据闭环：学习进度读取 + 雅思三件套 + 生词本艾宾浩斯复习（2026-08-03）
- [x] M3 AI 能力：DeepSeek 灵感懒加载 + AI 起草复盘 + 周报（2026-08-03）
- [ ] M4 集成：抖音提取异步任务 + Obsidian 联动 + 设置页

设计文档：`docs/superpowers/specs/2026-08-03-personal-workbench-design.md`
