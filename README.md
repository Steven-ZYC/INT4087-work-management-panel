# INT 4087 Group Project

`INT 4087 Web Database Applications for Data Analytics`

Authors:

- Steven Zhang Yancheng
- Ruby Wong Tsz Ching

This repository contains a lightweight web database application for team/project/task management with analytics-oriented views and APIs.

The project is organized around three main layers:

- `database structure`
- `web application pipeline`
- `analytics outputs`

---

## English

### Project Overview

This project is built as a lightweight database-backed web application with an analytics dashboard.

Main goals of the system:

- manage members, groups, projects, subprojects, and tasks
- preserve a clean relational database structure
- expose operational and analytics data through a simple Flask-based web pipeline
- support both live analytics and lightweight demo-mode trend data

### Technical Stack

- Backend: `Flask`
- Database: `SQLite`
- Frontend: `Jinja template + static JS/CSS`
- Dependency management: `uv`

### Project Structure

```text
groupproject/
├── groupproject.py             # Main Flask app: DB init, routes, analytics logic
├── templates/
│   └── index.html              # Main page template
├── static/
│   ├── app.js                  # Frontend state, API calls, analytics rendering
│   └── app.css                 # Styles
├── data/
│   └── analytics_snapshot.json # Demo-mode trend snapshot
├── work_management.db          # SQLite database
├── pyproject.toml              # Dependencies
├── uv.lock                     # uv lockfile
└── README.md
```

### Database Structure

The relational model currently includes:

- `member`
- `team_group`
- `member_group`
- `project`
- `subproject`
- `task`
- `task_assignment`

Key design points:

- normalized relational structure
- foreign-key relationships
- project -> subproject -> task hierarchy
- task fields for `deadline`, `urgency_score`, `subjective_importance`, and `status`
- member/task linkage for workload analysis

These tables support both application operations and analytics computation.

### Web Application Pipeline

The web pipeline is straightforward:

1. Flask serves the main page from `templates/index.html`
2. frontend JS in `static/app.js` requests API data
3. Flask routes query SQLite
4. JSON responses are rendered into management and analytics views

This keeps the request/data/rendering path explicit and easy to reproduce.

### Current Features

- member management
- group management
- project management
- subproject management
- task creation and admin editing
- dashboard for overdue and urgent items
- analytics page with second-level tabs:
  - `Overview`
  - `Risk`
  - `Pressure`
  - `Trends`
  - `Details`

### Analytics Outputs

`/api/analytics/summary` currently returns:

- `summary`
- `project_health`
- `overdue_projects`
- `project_risk_bands`
- `member_workload`
- `quadrants`
- `quadrant_tasks`
- `status_counts`
- `deadline_buckets`
- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`
- `urgent_task_list`
- `top_risky_tasks`

### Timezone Rule

All analytics calculations and display logic use:

- `HKT`
- `Asia/Hong_Kong`
- `UTC+08:00`

### Demo Snapshot Mode

The project includes a lightweight demo-mode analytics overlay.

Config:

- `ANALYTICS_DEMO_MODE=true|false`
- `ANALYTICS_SNAPSHOT_FILE=./data/analytics_snapshot.json`

When demo mode is enabled:

- selected trend fields are read from the snapshot JSON

When demo mode is disabled:

- mock snapshot data is ignored
- trend values fall back to live computation

Currently snapshot-overridable trend fields:

- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`

---

### Reproduction Guide

This section is intended for reproducing the project locally.

#### 1. Environment

- Python `>= 3.10`
- `uv`

#### 2. Install dependencies

```bash
uv sync
```

#### 3. Run the project

```bash
uv run python groupproject.py
```

Open:

```text
http://127.0.0.1:5000
```

#### 4. Default demo accounts

- `s0000001 / admin`
- `s0000002 / leader`
- `s0000003 / member`
- `s0000004 / advisor`

#### 5. Reproduce demo analytics mode

Use the default configuration:

- `ANALYTICS_DEMO_MODE=true`

This will read:

- `data/analytics_snapshot.json`

#### 6. Reproduce live analytics mode

Run with:

```bash
ANALYTICS_DEMO_MODE=false uv run python groupproject.py
```

#### 7. Reproduce a production-style run

If needed, the app can also be started with:

```bash
uv run gunicorn -w 2 -b 127.0.0.1:8000 groupproject:app
```

---

## 简体中文

### 项目概述

这个项目是一个轻量的 Web 数据库应用，包含团队/项目/任务管理，以及面向分析的 dashboard 和 API。

项目主要由三层组成：

- `数据库结构`
- `Web 应用 pipeline`
- `analytics 输出`

### 技术栈

- 后端：`Flask`
- 数据库：`SQLite`
- 前端：`Jinja 模板 + 静态 JS/CSS`
- 依赖管理：`uv`

### 项目结构

```text
groupproject/
├── groupproject.py             # Flask 主程序：建表、路由、analytics 逻辑
├── templates/
│   └── index.html              # 主页面模板
├── static/
│   ├── app.js                  # 前端状态、接口调用、分析页渲染
│   └── app.css                 # 样式
├── data/
│   └── analytics_snapshot.json # demo 模式趋势数据
├── work_management.db          # SQLite 数据库
├── pyproject.toml              # 依赖
├── uv.lock                     # uv 锁文件
└── README.md
```

### 数据库结构

当前关系模型包括：

- `member`
- `team_group`
- `member_group`
- `project`
- `subproject`
- `task`
- `task_assignment`

关键设计点：

- 规范化关系结构
- 外键关联
- `project -> subproject -> task` 层级
- task 包含 `deadline`、`urgency_score`、`subjective_importance`、`status`
- member 与 task 的关联可用于负载分析

这些表同时服务于业务操作和 analytics 计算。

### Web 应用 Pipeline

Web 数据流如下：

1. Flask 返回 `templates/index.html`
2. 前端 `static/app.js` 请求 API
3. Flask 路由查询 SQLite
4. 后端返回 JSON
5. 前端渲染管理页与 analytics 页

### 当前功能

- 成员管理
- 小组管理
- 项目管理
- 子项目管理
- 任务新增与管理员编辑
- overdue / urgent dashboard
- analytics 页面二级菜单：
  - `Overview`
  - `Risk`
  - `Pressure`
  - `Trends`
  - `Details`

### 当前 Analytics 输出

`/api/analytics/summary` 当前包含：

- `summary`
- `project_health`
- `overdue_projects`
- `project_risk_bands`
- `member_workload`
- `quadrants`
- `quadrant_tasks`
- `status_counts`
- `deadline_buckets`
- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`
- `urgent_task_list`
- `top_risky_tasks`

### 时间口径

项目统一使用：

- `HKT`
- `Asia/Hong_Kong`
- `UTC+08:00`

### Demo Snapshot 模式

项目包含一个轻量的 demo analytics 覆盖层。

配置项：

- `ANALYTICS_DEMO_MODE=true|false`
- `ANALYTICS_SNAPSHOT_FILE=./data/analytics_snapshot.json`

当 demo 模式开启时：

- 部分趋势字段会从 snapshot JSON 中读取

当 demo 模式关闭时：

- 自动忽略 mock snapshot
- 趋势分析回到 live 计算

当前可被 snapshot 覆盖的趋势字段：

- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`

### 复现方法

这一部分用于老师本地复现项目。

#### 1. 环境要求

- Python `>= 3.10`
- `uv`

#### 2. 安装依赖

```bash
uv sync
```

#### 3. 启动项目

```bash
uv run python groupproject.py
```

访问：

```text
http://127.0.0.1:5000
```

#### 4. 默认演示账号

- `s0000001 / admin`
- `s0000002 / leader`
- `s0000003 / member`
- `s0000004 / advisor`

#### 5. 复现 demo analytics 模式

默认情况下：

- `ANALYTICS_DEMO_MODE=true`

此时会读取：

- `data/analytics_snapshot.json`

#### 6. 复现 live analytics 模式

```bash
ANALYTICS_DEMO_MODE=false uv run python groupproject.py
```

#### 7. 复现接近生产的运行方式

如需要，也可使用：

```bash
uv run gunicorn -w 2 -b 127.0.0.1:8000 groupproject:app
```

---

## 繁體中文

### 專案概述

這個專案是一個輕量的 Web 資料庫應用，包含團隊/專案/任務管理，以及面向分析的 dashboard 和 API。

專案主要由三層組成：

- `資料庫結構`
- `Web 應用 pipeline`
- `analytics 輸出`

### 技術棧

- 後端：`Flask`
- 資料庫：`SQLite`
- 前端：`Jinja 模板 + 靜態 JS/CSS`
- 相依管理：`uv`

### 專案結構

```text
groupproject/
├── groupproject.py             # Flask 主程式：建表、路由、analytics 邏輯
├── templates/
│   └── index.html              # 主頁模板
├── static/
│   ├── app.js                  # 前端狀態、API 呼叫、分析頁渲染
│   └── app.css                 # 樣式
├── data/
│   └── analytics_snapshot.json # demo 模式趨勢資料
├── work_management.db          # SQLite 資料庫
├── pyproject.toml              # 相依套件
├── uv.lock                     # uv lockfile
└── README.md
```

### 資料庫結構

目前的關聯模型包括：

- `member`
- `team_group`
- `member_group`
- `project`
- `subproject`
- `task`
- `task_assignment`

關鍵設計點：

- 正規化關聯結構
- 外鍵關聯
- `project -> subproject -> task` 階層
- task 包含 `deadline`、`urgency_score`、`subjective_importance`、`status`
- member 與 task 的關聯可用於負載分析

這些資料表同時支援業務操作與 analytics 計算。

### Web 應用 Pipeline

Web 資料流如下：

1. Flask 回傳 `templates/index.html`
2. 前端 `static/app.js` 呼叫 API
3. Flask 路由查詢 SQLite
4. 後端回傳 JSON
5. 前端渲染管理頁與 analytics 頁

### 目前功能

- 成員管理
- 小組管理
- 專案管理
- 子專案管理
- 任務新增與管理員編輯
- overdue / urgent dashboard
- analytics 頁面二級選單：
  - `Overview`
  - `Risk`
  - `Pressure`
  - `Trends`
  - `Details`

### 目前 Analytics 輸出

`/api/analytics/summary` 目前包含：

- `summary`
- `project_health`
- `overdue_projects`
- `project_risk_bands`
- `member_workload`
- `quadrants`
- `quadrant_tasks`
- `status_counts`
- `deadline_buckets`
- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`
- `urgent_task_list`
- `top_risky_tasks`

### 時間口徑

專案統一使用：

- `HKT`
- `Asia/Hong_Kong`
- `UTC+08:00`

### Demo Snapshot 模式

專案包含一個輕量的 demo analytics 覆蓋層。

設定：

- `ANALYTICS_DEMO_MODE=true|false`
- `ANALYTICS_SNAPSHOT_FILE=./data/analytics_snapshot.json`

當 demo 模式開啟時：

- 部分趨勢欄位會從 snapshot JSON 讀取

當 demo 模式關閉時：

- 自動忽略 mock snapshot
- 趨勢分析回到 live 計算

目前可被 snapshot 覆蓋的趨勢欄位：

- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`

### 復現方法

這一部分用於老師本地復現專案。

#### 1. 環境需求

- Python `>= 3.10`
- `uv`

#### 2. 安裝依賴

```bash
uv sync
```

#### 3. 啟動專案

```bash
uv run python groupproject.py
```

訪問：

```text
http://127.0.0.1:5000
```

#### 4. 預設展示帳號

- `s0000001 / admin`
- `s0000002 / leader`
- `s0000003 / member`
- `s0000004 / advisor`

#### 5. 復現 demo analytics 模式

預設情況下：

- `ANALYTICS_DEMO_MODE=true`

此時會讀取：

- `data/analytics_snapshot.json`

#### 6. 復現 live analytics 模式

```bash
ANALYTICS_DEMO_MODE=false uv run python groupproject.py
```

#### 7. 復現接近生產的執行方式

如有需要，也可以使用：

```bash
uv run gunicorn -w 2 -b 127.0.0.1:8000 groupproject:app
```
