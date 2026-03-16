# INT 4087 Group Project

`INT 4087 Web Database Applications for Data Analytics`

作者：

- Steven Zhang Yancheng
- Ruby Wong Tsz Ching

语言版本：

- English：`README.md`
- 简体中文：`README-zh-CN.md`
- 繁體中文：`README-zh-HK.md`

这是一个轻量的 Web 数据库应用，包含团队/项目/任务管理，以及面向分析的 dashboard 和 API。

项目主要由三层组成：

- `数据库结构`
- `Web 应用 pipeline`
- `analytics 输出`

## 项目概述

这个项目是一个基于数据库的轻量 Web 应用，并带有 analytics dashboard。

系统的主要目标：

- 管理 members、groups、projects、subprojects 和 tasks
- 保持清晰的关系型数据库结构
- 通过简单的 Flask web pipeline 提供业务数据和分析数据
- 同时支持 live analytics 和轻量 demo 趋势数据

## 技术栈

- 后端：`Flask`
- 数据库：`SQLite`
- 前端：`Jinja 模板 + 静态 JS/CSS`
- 依赖管理：`uv`

## 项目结构

```text
INT4087-work-management-panel/
├── groupproject.py              # Flask 主程序：建表、路由、analytics 逻辑
├── templates/
│   └── index.html               # 主页面模板
├── static/
│   ├── app.js                   # 前端状态、接口调用、分析页渲染
│   └── app.css                  # 样式
├── data/
│   └── analytics_snapshot.json  # demo 模式趋势数据
├── work_management.db           # SQLite 数据库
├── pyproject.toml               # 依赖
├── uv.lock                      # uv 锁文件
├── README.md                    # English
├── README-zh-CN.md              # 简体中文
└── README-zh-HK.md              # 繁體中文
```

## 数据库结构

当前关系模型包含以下数据表。

### `member`

- `member_id`：整型主键
- `student_id`：唯一学号
- `password_hash`：密码哈希
- `name`：成员姓名
- `email`：唯一邮箱
- `role`：`admin`、`leader`、`member`、`advisor`
- `created_at`：创建时间

### `team_group`

- `group_id`：整型主键
- `group_name`：唯一小组名
- `description`：小组描述
- `created_at`：创建时间

### `member_group`

- `member_id`：指向 `member` 的外键
- `group_id`：指向 `team_group` 的外键
- `joined_at`：加入时间
- 联合主键：`(member_id, group_id)`

### `project`

- `project_id`：整型主键
- `title`：项目标题
- `description`：项目描述
- `status`：`planning`、`active`、`on_hold`、`completed`、`cancelled`
- `owner_member_id`：指向 `member` 的外键
- `created_by`：指向 `member` 的外键
- `start_date`：可选开始日期
- `end_date`：可选结束日期
- `created_at`：创建时间

### `subproject`

- `subproject_id`：整型主键
- `project_id`：指向 `project` 的外键
- `title`：子项目标题
- `description`：子项目描述
- `status`：`planning`、`active`、`on_hold`、`completed`、`cancelled`
- `owner_member_id`：指向 `member` 的外键
- `created_by`：指向 `member` 的外键
- `start_date`：可选开始日期
- `end_date`：可选结束日期
- `created_at`：创建时间

### `task`

- `task_id`：整型主键
- `subproject_id`：指向 `subproject` 的外键
- `title`：任务标题
- `description`：任务描述
- `status`：`todo`、`in_progress`、`blocked`、`done`
- `subjective_importance`：`[0,1]` 区间的重要度
- `deadline`：可选截止时间
- `urgency_score`：紧急度数值
- `created_by`：指向 `member` 的外键
- `created_at`：创建时间
- `updated_at`：更新时间

### `task_assignment`

- `task_id`：指向 `task` 的外键
- `member_id`：指向 `member` 的外键
- `responsibility_type`：`owner`、`helper`、`reviewer`
- `assigned_at`：分配时间
- 联合主键：`(task_id, member_id)`

## Web 应用 Pipeline

Web 数据流如下：

1. Flask 从 `templates/index.html` 返回主页面
2. `static/app.js` 请求后端 API
3. Flask 路由查询 SQLite
4. 后端返回 JSON
5. 前端渲染管理页和 analytics 页

## 当前功能

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

## 当前 Analytics 输出

`/api/analytics/summary` 当前返回：

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

## 时间口径

所有 analytics 计算和展示统一使用：

- `HKT`
- `Asia/Hong_Kong`
- `UTC+08:00`

## Demo Snapshot 模式

项目包含一个轻量的 demo-mode analytics 覆盖层。

配置项：

- `ANALYTICS_DEMO_MODE=true|false`
- `ANALYTICS_SNAPSHOT_FILE=./data/analytics_snapshot.json`

当 demo 模式开启时：

- 部分趋势字段会从 snapshot JSON 中读取

当 demo 模式关闭时：

- 自动忽略 mock snapshot
- 趋势字段回到 live 计算

当前可被 snapshot 覆盖的趋势字段：

- `deadline_pressure_series`
- `workload_pressure`
- `project_risk_trend`

## 复现方法

### 1. 环境要求

- Python `>= 3.10`
- `uv`

### 2. 安装依赖

```bash
uv sync
```

### 3. 启动项目

```bash
uv run python groupproject.py
```

访问：

```text
http://127.0.0.1:5000
```

### 4. 默认演示账号

- `s0000001 / admin`
- `s0000002 / leader`
- `s0000003 / member`
- `s0000004 / advisor`

### 5. 复现 demo analytics 模式

默认情况下：

- `ANALYTICS_DEMO_MODE=true`

此时会读取：

- `data/analytics_snapshot.json`

### 6. 复现 live analytics 模式

```bash
ANALYTICS_DEMO_MODE=false uv run python groupproject.py
```

### 7. 复现接近生产的运行方式

如需要，也可使用：

```bash
uv run gunicorn -w 2 -b 127.0.0.1:8000 groupproject:app
```
