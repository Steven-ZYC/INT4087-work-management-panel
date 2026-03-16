# INT 4087 Group Project

`INT 4087 Web Database Applications for Data Analytics`

作者：

- Steven Zhang Yancheng
- Ruby Wong Tsz Ching

語言版本：

- English：`README.md`
- 简体中文：`README-zh-CN.md`
- 繁體中文：`README-zh-HK.md`

這是一個輕量的 Web 資料庫應用，包含團隊/專案/任務管理，以及面向分析的 dashboard 和 API。

專案主要由三層組成：

- `資料庫結構`
- `Web 應用 pipeline`
- `analytics 輸出`

## 專案概述

這個專案是一個基於資料庫的輕量 Web 應用，並帶有 analytics dashboard。

系統的主要目標：

- 管理 members、groups、projects、subprojects 和 tasks
- 保持清晰的關係型資料庫結構
- 透過簡單的 Flask web pipeline 提供業務資料和分析資料
- 同時支援 live analytics 和輕量 demo 趨勢資料

## 技術棧

- 後端：`Flask`
- 資料庫：`SQLite`
- 前端：`Jinja 模板 + 靜態 JS/CSS`
- 相依管理：`uv`

## 專案結構

```text
INT4087-work-management-panel/
├── groupproject.py              # Flask 主程式：建表、路由、analytics 邏輯
├── templates/
│   └── index.html               # 主頁模板
├── static/
│   ├── app.js                   # 前端狀態、API 呼叫、分析頁渲染
│   └── app.css                  # 樣式
├── data/
│   └── analytics_snapshot.json  # demo 模式趨勢資料
├── work_management.db           # SQLite 資料庫
├── pyproject.toml               # 相依套件
├── uv.lock                      # uv lockfile
├── README.md                    # English
├── README-zh-CN.md              # 简体中文
└── README-zh-HK.md              # 繁體中文
```

## 資料庫結構

目前的關聯模型包含以下資料表。

### `member`

- `member_id`：整型主鍵
- `student_id`：唯一學號
- `password_hash`：密碼雜湊
- `name`：成員姓名
- `email`：唯一電郵
- `role`：`admin`、`leader`、`member`、`advisor`
- `created_at`：建立時間

### `team_group`

- `group_id`：整型主鍵
- `group_name`：唯一小組名稱
- `description`：小組描述
- `created_at`：建立時間

### `member_group`

- `member_id`：指向 `member` 的外鍵
- `group_id`：指向 `team_group` 的外鍵
- `joined_at`：加入時間
- 聯合主鍵：`(member_id, group_id)`

### `project`

- `project_id`：整型主鍵
- `title`：專案標題
- `description`：專案描述
- `status`：`planning`、`active`、`on_hold`、`completed`、`cancelled`
- `owner_member_id`：指向 `member` 的外鍵
- `created_by`：指向 `member` 的外鍵
- `start_date`：可選開始日期
- `end_date`：可選結束日期
- `created_at`：建立時間

### `subproject`

- `subproject_id`：整型主鍵
- `project_id`：指向 `project` 的外鍵
- `title`：子專案標題
- `description`：子專案描述
- `status`：`planning`、`active`、`on_hold`、`completed`、`cancelled`
- `owner_member_id`：指向 `member` 的外鍵
- `created_by`：指向 `member` 的外鍵
- `start_date`：可選開始日期
- `end_date`：可選結束日期
- `created_at`：建立時間

### `task`

- `task_id`：整型主鍵
- `subproject_id`：指向 `subproject` 的外鍵
- `title`：任務標題
- `description`：任務描述
- `status`：`todo`、`in_progress`、`blocked`、`done`
- `subjective_importance`：`[0,1]` 區間的重要度
- `deadline`：可選截止時間
- `urgency_score`：緊急度數值
- `created_by`：指向 `member` 的外鍵
- `created_at`：建立時間
- `updated_at`：更新時間

### `task_assignment`

- `task_id`：指向 `task` 的外鍵
- `member_id`：指向 `member` 的外鍵
- `responsibility_type`：`owner`、`helper`、`reviewer`
- `assigned_at`：分配時間
- 聯合主鍵：`(task_id, member_id)`

## Web 應用 Pipeline

Web 資料流如下：

1. Flask 從 `templates/index.html` 回傳主頁
2. `static/app.js` 呼叫後端 API
3. Flask 路由查詢 SQLite
4. 後端回傳 JSON
5. 前端渲染管理頁和 analytics 頁

## 目前功能

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

## 目前 Analytics 輸出

`/api/analytics/summary` 目前回傳：

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

## 時間口徑

所有 analytics 計算與展示統一使用：

- `HKT`
- `Asia/Hong_Kong`
- `UTC+08:00`

## Demo Snapshot 模式

專案包含一個輕量的 demo-mode analytics 覆蓋層。

設定：

- `ANALYTICS_DEMO_MODE=true|false`
- `ANALYTICS_SNAPSHOT_FILE=./data/analytics_snapshot.json`

當 demo 模式開啟時：

- 部分趨勢欄位會從 snapshot JSON 中讀取

當 demo 模式關閉時：

- 自動忽略 mock snapshot
- 趨勢欄位回到 live 計算

目前可被 snapshot 覆蓋的趨勢欄位：

- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`

## 復現方法

### 1. 環境需求

- Python `>= 3.10`
- `uv`

### 2. 安裝依賴

```bash
uv sync
```

### 3. 啟動專案

```bash
uv run python groupproject.py
```

訪問：

```text
http://127.0.0.1:5000
```

### 4. 預設展示帳號

- `s0000001 / admin`
- `s0000002 / leader`
- `s0000003 / member`
- `s0000004 / advisor`

### 5. 復現 demo analytics 模式

預設情況下：

- `ANALYTICS_DEMO_MODE=true`

此時會讀取：

- `data/analytics_snapshot.json`

### 6. 復現 live analytics 模式

```bash
ANALYTICS_DEMO_MODE=false uv run python groupproject.py
```

### 7. 復現接近生產的執行方式

如有需要，也可以使用：

```bash
uv run gunicorn -w 2 -b 127.0.0.1:8000 groupproject:app
```
