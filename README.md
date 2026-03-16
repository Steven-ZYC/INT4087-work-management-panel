# INT 4087 Group Project

`INT 4087 Web Database Applications for Data Analytics`

Authors:

- Steven Zhang Yancheng
- Ruby Wong Tsz Ching

Language versions:

- English: `README.md`
- 简体中文: `README-zh-CN.md`
- 繁體中文: `README-zh-HK.md`

This repository contains a lightweight web database application for team/project/task management with analytics-oriented views and APIs.

The project is organized around three main layers:

- `database structure`
- `web application pipeline`
- `analytics outputs`

## Project Overview

This project is built as a lightweight database-backed web application with an analytics dashboard.

Main goals of the system:

- manage members, groups, projects, subprojects, and tasks
- preserve a clean relational database structure
- expose operational and analytics data through a simple Flask-based web pipeline
- support both live analytics and lightweight demo-mode trend data

## Technical Stack

- Backend: `Flask`
- Database: `SQLite`
- Frontend: `Jinja template + static JS/CSS`
- Dependency management: `uv`

## Project Structure

```text
INT4087-work-management-panel/
├── groupproject.py              # Main Flask app: DB init, routes, analytics logic
├── templates/
│   └── index.html               # Main page template
├── static/
│   ├── app.js                   # Frontend state, API calls, analytics rendering
│   └── app.css                  # Styles
├── data/
│   └── analytics_snapshot.json  # Demo-mode trend snapshot
├── work_management.db           # SQLite database
├── pyproject.toml               # Dependencies
├── uv.lock                      # uv lockfile
├── README.md                    # English
├── README-zh-CN.md              # Simplified Chinese
└── README-zh-HK.md              # Traditional Chinese
```

## Database Structure

The current relational model includes the following tables.

### `member`

- `member_id`: integer primary key
- `student_id`: unique student identifier
- `password_hash`: hashed password
- `name`: member display name
- `email`: unique email
- `role`: one of `admin`, `leader`, `member`, `advisor`
- `created_at`: record creation time

### `team_group`

- `group_id`: integer primary key
- `group_name`: unique group name
- `description`: group description
- `created_at`: record creation time

### `member_group`

- `member_id`: foreign key to `member`
- `group_id`: foreign key to `team_group`
- `joined_at`: join time
- composite primary key: `(member_id, group_id)`

### `project`

- `project_id`: integer primary key
- `title`: project title
- `description`: project description
- `status`: one of `planning`, `active`, `on_hold`, `completed`, `cancelled`
- `owner_member_id`: foreign key to `member`
- `created_by`: foreign key to `member`
- `start_date`: optional start date
- `end_date`: optional end date
- `created_at`: record creation time

### `subproject`

- `subproject_id`: integer primary key
- `project_id`: foreign key to `project`
- `title`: subproject title
- `description`: subproject description
- `status`: one of `planning`, `active`, `on_hold`, `completed`, `cancelled`
- `owner_member_id`: foreign key to `member`
- `created_by`: foreign key to `member`
- `start_date`: optional start date
- `end_date`: optional end date
- `created_at`: record creation time

### `task`

- `task_id`: integer primary key
- `subproject_id`: foreign key to `subproject`
- `title`: task title
- `description`: task description
- `status`: one of `todo`, `in_progress`, `blocked`, `done`
- `subjective_importance`: numeric importance in `[0, 1]`
- `deadline`: optional deadline
- `urgency_score`: numeric urgency score
- `created_by`: foreign key to `member`
- `created_at`: record creation time
- `updated_at`: last update time

### `task_assignment`

- `task_id`: foreign key to `task`
- `member_id`: foreign key to `member`
- `responsibility_type`: one of `owner`, `helper`, `reviewer`
- `assigned_at`: assignment time
- composite primary key: `(task_id, member_id)`

## Web Application Pipeline

The web pipeline is straightforward:

1. Flask serves the main page from `templates/index.html`
2. frontend JS in `static/app.js` requests API data
3. Flask routes query SQLite
4. JSON responses are rendered into management and analytics views

## Current Features

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

## Analytics Outputs

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

## Timezone Rule

All analytics calculations and display logic use:

- `HKT`
- `Asia/Hong_Kong`
- `UTC+08:00`

## Demo Snapshot Mode

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

## Reproduction Guide

### 1. Environment

- Python `>= 3.10`
- `uv`

### 2. Install dependencies

```bash
uv sync
```

### 3. Run the project

```bash
uv run python groupproject.py
```

Open:

```text
http://127.0.0.1:5000
```

### 4. Default demo accounts

- `s0000001 / admin`
- `s0000002 / leader`
- `s0000003 / member`
- `s0000004 / advisor`

### 5. Reproduce demo analytics mode

Use the default configuration:

- `ANALYTICS_DEMO_MODE=true`

This will read:

- `data/analytics_snapshot.json`

### 6. Reproduce live analytics mode

Run with:

```bash
ANALYTICS_DEMO_MODE=false uv run python groupproject.py
```

### 7. Reproduce a production-style run

If needed, the app can also be started with:

```bash
uv run gunicorn -w 2 -b 127.0.0.1:8000 groupproject:app
```
