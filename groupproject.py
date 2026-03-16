import os
import json
import sqlite3
import threading
import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# 1. INITIALIZATION
# ==========================================

app = Flask(__name__)
app.secret_key = "super_secret_wms_key_for_sessions"
DB_NAME = "work_management.db"
MEMBER_ROLES = ("admin", "leader", "member", "advisor")
HKT = datetime.timezone(datetime.timedelta(hours=8), name="HKT")
BASE_DIR = Path(__file__).resolve().parent
ANALYTICS_DEMO_MODE = os.getenv("ANALYTICS_DEMO_MODE", "true").lower() in {"1", "true", "yes", "on"}
ANALYTICS_SNAPSHOT_FILE = Path(os.getenv("ANALYTICS_SNAPSHOT_FILE", str(BASE_DIR / "data" / "analytics_snapshot.json")))

# ==========================================
# 2. DATABASE
# ==========================================

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def now_hkt():
    return datetime.datetime.now(HKT)

def hkt_db_timestamp():
    return now_hkt().isoformat(timespec="seconds")

def parse_datetime_value(value, naive_tz=HKT):
    if not value:
        return None
    for parser in (datetime.datetime.fromisoformat,):
        try:
            dt = parser(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=naive_tz)
            return dt.astimezone(HKT)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.datetime.strptime(value, fmt).replace(tzinfo=naive_tz).astimezone(HKT)
        except ValueError:
            pass
    return None

def normalize_hkt_datetime(value, naive_tz=HKT):
    dt = parse_datetime_value(value, naive_tz=naive_tz)
    return dt.isoformat(timespec="seconds") if dt else value

def normalize_deadline_value(value):
    if not value:
        return ""
    return normalize_hkt_datetime(value, naive_tz=HKT)

def normalize_existing_db_timestamps(conn):
    column_timezones = {
        "member": {"created_at": datetime.timezone.utc},
        "team_group": {"created_at": datetime.timezone.utc},
        "member_group": {"joined_at": datetime.timezone.utc},
        "project": {"created_at": datetime.timezone.utc, "start_date": HKT, "end_date": HKT},
        "subproject": {"created_at": datetime.timezone.utc, "start_date": HKT, "end_date": HKT},
        "task": {"deadline": HKT, "created_at": datetime.timezone.utc, "updated_at": datetime.timezone.utc},
        "task_assignment": {"assigned_at": datetime.timezone.utc},
    }
    cursor = conn.cursor()
    for table, columns in column_timezones.items():
        select_cols = ", ".join(columns.keys())
        rows = cursor.execute(f"SELECT rowid AS __rowid__, {select_cols} FROM {table}").fetchall()
        for row in rows:
            updates = {}
            for column, naive_tz in columns.items():
                value = row[column]
                if not value:
                    continue
                normalized = normalize_hkt_datetime(value, naive_tz=naive_tz)
                if normalized != value:
                    updates[column] = normalized
            if not updates:
                continue
            assignments = ", ".join(f"{column} = ?" for column in updates)
            cursor.execute(
                f"UPDATE {table} SET {assignments} WHERE rowid = ?",
                (*updates.values(), row["__rowid__"])
            )

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS member (
            member_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id     TEXT NOT NULL UNIQUE,
            password_hash  TEXT NOT NULL,
            name           TEXT NOT NULL,
            email          TEXT NOT NULL UNIQUE,
            role           TEXT NOT NULL DEFAULT 'member'
                           CHECK (role IN ('admin', 'leader', 'member', 'advisor')),
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_group (
            group_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name      TEXT NOT NULL UNIQUE,
            description     TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS member_group (
            member_id       INTEGER NOT NULL,
            group_id        INTEGER NOT NULL,
            joined_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (member_id, group_id),
            FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES team_group(group_id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS project (
            project_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title             TEXT NOT NULL,
            description       TEXT,
            status            TEXT NOT NULL DEFAULT 'planning'
                              CHECK (status IN ('planning', 'active', 'on_hold', 'completed', 'cancelled')),
            owner_member_id   INTEGER,
            created_by        INTEGER,
            start_date        DATE,
            end_date          DATE,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_member_id) REFERENCES member(member_id) ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES member(member_id) ON DELETE SET NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subproject (
            subproject_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id         INTEGER NOT NULL,
            title              TEXT NOT NULL,
            description        TEXT,
            status             TEXT NOT NULL DEFAULT 'planning'
                               CHECK (status IN ('planning', 'active', 'on_hold', 'completed', 'cancelled')),
            owner_member_id    INTEGER,
            created_by         INTEGER,
            start_date         DATE,
            end_date           DATE,
            created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES project(project_id) ON DELETE CASCADE,
            FOREIGN KEY (owner_member_id) REFERENCES member(member_id) ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES member(member_id) ON DELETE SET NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task (
            task_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            subproject_id           INTEGER NOT NULL,
            title                   TEXT NOT NULL,
            description             TEXT DEFAULT '',
            status                  TEXT NOT NULL DEFAULT 'todo'
                                    CHECK (status IN ('todo', 'in_progress', 'blocked', 'done')),
            subjective_importance   REAL NOT NULL DEFAULT 0.5
                                    CHECK (subjective_importance >= 0 AND subjective_importance <= 1),
            deadline                DATETIME,
            urgency_score           REAL NOT NULL DEFAULT 0.5,
            created_by              INTEGER,
            created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subproject_id) REFERENCES subproject(subproject_id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES member(member_id) ON DELETE SET NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_assignment (
            task_id              INTEGER NOT NULL,
            member_id            INTEGER NOT NULL,
            responsibility_type  TEXT NOT NULL DEFAULT 'owner'
                                 CHECK (responsibility_type IN ('owner', 'helper', 'reviewer')),
            assigned_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (task_id, member_id),
            FOREIGN KEY (task_id) REFERENCES task(task_id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE
        );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_member_student_id ON member(student_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_member_email ON member(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_member_group_member ON member_group(member_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_member_group_group ON member_group(group_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_owner ON project(owner_member_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subproject_project ON subproject(project_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subproject_owner ON subproject(owner_member_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_subproject ON task(subproject_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_deadline ON task(deadline);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_assignment_member ON task_assignment(member_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_assignment_task ON task_assignment(task_id);")

        cursor.execute("SELECT COUNT(*) FROM member")
        if cursor.fetchone()[0] == 0:
            users = [
                ("s0000001", generate_password_hash("admin"), "Admin User", "admin@team.local", "admin"),
                ("s0000002", generate_password_hash("leader"), "Team Leader", "leader@team.local", "leader"),
                ("s0000003", generate_password_hash("member"), "Normal Member", "member@team.local", "member"),
                ("s0000004", generate_password_hash("advisor"), "Faculty Advisor", "advisor@team.local", "advisor"),
            ]
            cursor.executemany("""
                INSERT INTO member (student_id, password_hash, name, email, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [(*user, hkt_db_timestamp()) for user in users])

        cursor.execute("SELECT COUNT(*) FROM team_group")
        if cursor.fetchone()[0] == 0:
            groups = [
                ("Software", "Software development and control stack"),
                ("Hardware", "Electronics, PCB, power and wiring"),
                ("Mechanical", "Mechanical design and fabrication"),
                ("Media", "Documentation, visuals and outreach"),
            ]
            cursor.executemany("""
                INSERT INTO team_group (group_name, description, created_at)
                VALUES (?, ?, ?)
            """, [(*group, hkt_db_timestamp()) for group in groups])

        cursor.execute("SELECT COUNT(*) FROM member_group")
        if cursor.fetchone()[0] == 0:
            assignments = [
                (1, 1), (2, 1), (3, 1),
                (2, 2), (3, 3), (4, 4)
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO member_group (member_id, group_id, joined_at)
                VALUES (?, ?, ?)
            """, [(*assignment, hkt_db_timestamp()) for assignment in assignments])

        cursor.execute("SELECT COUNT(*) FROM project")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO project (title, description, status, owner_member_id, created_by, created_at)
                VALUES (?, ?, 'active', ?, ?, ?)
            """, ("Robocon 2026", "Main robotics competition project", 2, 1, hkt_db_timestamp()))
            project_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO subproject (project_id, title, description, status, owner_member_id, created_by, created_at)
                VALUES (?, ?, ?, 'active', ?, ?, ?)
            """, (project_id, "R2 Control Stack", "Motion control and local navigation", 2, 2, hkt_db_timestamp()))
            sp1 = cursor.lastrowid

            cursor.execute("""
                INSERT INTO subproject (project_id, title, description, status, owner_member_id, created_by, created_at)
                VALUES (?, ?, ?, 'planning', ?, ?, ?)
            """, (project_id, "Vision Pipeline", "Perception and target detection", 3, 2, hkt_db_timestamp()))
            sp2 = cursor.lastrowid

            cursor.execute("""
                INSERT INTO task (subproject_id, title, description, deadline, subjective_importance, urgency_score, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sp1, "Tune wheel PID", "Tune omniwheel PID gains", normalize_deadline_value("2026-03-20T20:00"), 0.8, 0.72, 2, hkt_db_timestamp(), hkt_db_timestamp()))
            task_id = cursor.lastrowid

            cursor.executemany("""
                INSERT INTO task_assignment (task_id, member_id, responsibility_type, assigned_at)
                VALUES (?, ?, ?, ?)
            """, [
                (task_id, 2, "owner", hkt_db_timestamp()),
                (task_id, 3, "helper", hkt_db_timestamp())
            ])

        extra_members = [
            ("s0000005", "Power Systems Lead", "power@team.local", "leader"),
            ("s0000006", "Embedded Engineer", "embedded@team.local", "member"),
            ("s0000007", "CAD Specialist", "cad@team.local", "member"),
            ("s0000008", "Manufacturing Coordinator", "fab@team.local", "member"),
            ("s0000009", "Media Operator", "media@team.local", "member"),
            ("s0000010", "Data Analyst", "data@team.local", "advisor"),
        ]
        for student_id, name, email, role in extra_members:
            cursor.execute("""
                INSERT OR IGNORE INTO member (student_id, password_hash, name, email, role)
                VALUES (?, ?, ?, ?, ?)
            """, (student_id, generate_password_hash("member"), name, email, role))

        cursor.execute("""
            INSERT OR IGNORE INTO team_group (group_name, description)
            VALUES (?, ?)
        """, ("Operations", "Procurement, logistics, and competition support"))

        group_ids = {
            row["group_name"]: row["group_id"]
            for row in cursor.execute("SELECT group_id, group_name FROM team_group").fetchall()
        }
        member_ids = {
            row["student_id"]: row["member_id"]
            for row in cursor.execute("SELECT member_id, student_id FROM member").fetchall()
        }

        extra_assignments = [
            ("s0000005", "Hardware"),
            ("s0000006", "Hardware"),
            ("s0000006", "Software"),
            ("s0000007", "Mechanical"),
            ("s0000008", "Operations"),
            ("s0000009", "Media"),
            ("s0000010", "Software"),
        ]
        for student_id, group_name in extra_assignments:
            member_id = member_ids.get(student_id)
            group_id = group_ids.get(group_name)
            if member_id and group_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO member_group (member_id, group_id)
                    VALUES (?, ?)
                """, (member_id, group_id))

        project_specs = [
            ("Field Reliability Sprint", "Stability and recovery hardening", "active", "s0000005", "s0000001"),
            ("Driver Dashboard", "Operator station telemetry and controls", "planning", "s0000010", "s0000002"),
            ("Outreach Platform", "Competition media and sponsor portal", "active", "s0000009", "s0000001"),
        ]
        project_ids = {
            row["title"]: row["project_id"]
            for row in cursor.execute("SELECT project_id, title FROM project").fetchall()
        }

        for title, description, status, owner_student_id, creator_student_id in project_specs:
            existing = cursor.execute(
                "SELECT project_id FROM project WHERE title = ?",
                (title,)
            ).fetchone()
            if existing:
                project_ids[title] = existing["project_id"]
                continue

            cursor.execute("""
                INSERT INTO project (title, description, status, owner_member_id, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (
                title,
                description,
                status,
                member_ids.get(owner_student_id),
                member_ids.get(creator_student_id)
            ))
            project_ids[title] = cursor.lastrowid

        subproject_specs = [
            ("Robocon 2026", "R2 Control Stack", "Motion control and local navigation", "active", "s0000002", "s0000002"),
            ("Robocon 2026", "Vision Pipeline", "Perception and target detection", "planning", "s0000003", "s0000002"),
            ("Robocon 2026", "Field Reliability Sprint", "Failure injection, logging, and watchdogs", "active", "s0000005", "s0000001"),
            ("Robocon 2026", "Driver Dashboard", "Match control panel, telemetry views, and alerts", "active", "s0000010", "s0000002"),
            ("Outreach Platform", "Sponsor CMS", "Landing pages and sponsor visibility tools", "active", "s0000009", "s0000001"),
            ("Outreach Platform", "Analytics Feed", "Weekly KPI dashboards for outreach performance", "planning", "s0000010", "s0000001"),
        ]
        subproject_ids = {
            row["title"]: row["subproject_id"]
            for row in cursor.execute("SELECT subproject_id, title FROM subproject").fetchall()
        }
        for project_title, title, description, status, owner_student_id, creator_student_id in subproject_specs:
            existing = cursor.execute(
                "SELECT subproject_id FROM subproject WHERE title = ?",
                (title,)
            ).fetchone()
            if existing:
                subproject_ids[title] = existing["subproject_id"]
                continue

            cursor.execute("""
                INSERT INTO subproject (project_id, title, description, status, owner_member_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_ids[project_title],
                title,
                description,
                status,
                member_ids.get(owner_student_id),
                member_ids.get(creator_student_id)
            ))
            subproject_ids[title] = cursor.lastrowid

        task_specs = [
            ("R2 Control Stack", "Tune wheel PID", "Tune omniwheel PID gains", "todo", "2026-03-20T20:00", 0.80, 0.72, "s0000002", ["s0000002", "s0000003"]),
            ("Vision Pipeline", "Dataset cleanup", "Remove noisy labels from scrimmage captures", "in_progress", "2026-03-28T18:00", 0.67, 0.49, "s0000003", ["s0000003"]),
            ("Field Reliability Sprint", "Watchdog recovery test", "Validate reboot path after controller freeze", "todo", "2026-03-17T22:00", 0.92, 0.96, "s0000005", ["s0000005", "s0000006"]),
            ("Field Reliability Sprint", "Battery swap drill", "Measure pit stop battery replacement timing", "todo", "2026-03-16T21:00", 0.88, 0.99, "s0000005", ["s0000005", "s0000008"]),
            ("Field Reliability Sprint", "Failure log review", "Classify the top 20 failure signatures", "done", "2026-03-14T12:00", 0.76, 0.83, "s0000010", ["s0000010"]),
            ("Driver Dashboard", "Latency overlay", "Show radio delay and packet loss trend", "in_progress", "2026-03-24T19:30", 0.73, 0.61, "s0000010", ["s0000010", "s0000002"]),
            ("Driver Dashboard", "Preset shortcuts", "One-click action presets for operator", "todo", "2026-04-02T17:00", 0.58, 0.38, "s0000002", ["s0000002"]),
            ("Sponsor CMS", "Sponsor asset upload", "Batch upload and validate sponsor media kit files", "todo", "2026-03-30T12:00", 0.54, 0.41, "s0000009", ["s0000009"]),
            ("Sponsor CMS", "Booth checklist", "Prepare sponsor booth collateral and QR material", "todo", "2026-03-18T09:00", 0.61, 0.79, "s0000009", ["s0000008", "s0000009"]),
            ("Analytics Feed", "Weekly KPI query", "Build SQL for weekly reach and conversion metrics", "todo", "", 0.82, 0.46, "s0000010", ["s0000010"]),
            ("Analytics Feed", "Data warehouse schema", "Prepare star schema for future analytics features", "todo", "2026-04-10T18:00", 0.90, 0.33, "s0000010", ["s0000010", "s0000006"]),
            ("R2 Control Stack", "R2 kinematics", "Refine mecanum kinematics and validate odometry", "todo", "", 1.00, 1.00, "s0000002", ["s0000002"]),
        ]
        existing_tasks = {
            row["title"]: row["task_id"]
            for row in cursor.execute("SELECT task_id, title FROM task").fetchall()
        }
        for subproject_title, title, description, status, deadline, importance, urgency, creator_student_id, assignees in task_specs:
            if title in existing_tasks:
                continue

            cursor.execute("""
                INSERT INTO task (
                    subproject_id, title, description, status, deadline,
                    subjective_importance, urgency_score, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subproject_ids[subproject_title],
                title,
                description,
                status,
                deadline,
                importance,
                urgency,
                member_ids.get(creator_student_id)
            ))
            task_id = cursor.lastrowid

            for student_id in assignees:
                member_id = member_ids.get(student_id)
                if member_id:
                    cursor.execute("""
                        INSERT OR IGNORE INTO task_assignment (task_id, member_id, responsibility_type)
                        VALUES (?, ?, 'owner')
                    """, (task_id, member_id))

        normalize_existing_db_timestamps(conn)
        conn.commit()

    print("Database initialized.")

init_db()

# ==========================================
# 3. HELPERS
# ==========================================

def calculate_urgency(deadline_str, importance):
    try:
        deadline = parse_datetime_value(deadline_str, naive_tz=HKT)
        now = now_hkt()
        hours_left = (deadline - now).total_seconds() / 3600
        time_factor = max(0, (72 - hours_left) / 72) if hours_left < 72 else 0
        if hours_left <= 0:
            time_factor = 1.0
        return round((time_factor * 0.7) + (float(importance) * 0.3), 2)
    except Exception:
        return 0.5

def current_user_id():
    return session.get("user_id")

def current_role():
    return session.get("role")

def is_admin():
    return current_role() == "admin"

def is_leader():
    return current_role() in ["admin", "leader"]

def can_manage_structure():
    return current_role() in ["admin", "leader"]

def can_edit_member(target_member_id):
    return is_leader() or current_user_id() == target_member_id

def to_hkt_iso(value):
    if not value:
        return None
    parsed = value if isinstance(value, datetime.datetime) else parse_datetime_value(value, naive_tz=HKT)
    if not parsed:
        return None
    return parsed.astimezone(HKT).isoformat(timespec="seconds")

def safe_ratio(numerator, denominator):
    if not denominator:
        return 0.0
    return round(numerator / denominator, 2)

def load_demo_analytics_snapshot():
    if not ANALYTICS_DEMO_MODE or not ANALYTICS_SNAPSHOT_FILE.exists():
        return None
    try:
        with ANALYTICS_SNAPSHOT_FILE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload

def build_analytics_summary(conn):
    now = now_hkt()
    task_rows = conn.execute("""
        SELECT
            t.task_id, t.title, t.description, t.status, t.deadline,
            t.subjective_importance, t.urgency_score,
            sp.subproject_id, sp.title AS subproject_title,
            p.project_id, p.title AS project_title
        FROM task t
        JOIN subproject sp ON t.subproject_id = sp.subproject_id
        JOIN project p ON sp.project_id = p.project_id
    """).fetchall()
    member_rows = conn.execute("""
        SELECT
            m.member_id, m.name, m.role,
            GROUP_CONCAT(DISTINCT g.group_name) AS group_names
        FROM member m
        LEFT JOIN member_group mg ON m.member_id = mg.member_id
        LEFT JOIN team_group g ON mg.group_id = g.group_id
        GROUP BY m.member_id
        ORDER BY m.member_id ASC
    """).fetchall()
    assignment_rows = conn.execute("""
        SELECT ta.member_id, t.task_id, t.status, t.deadline, t.urgency_score
        FROM task_assignment ta
        JOIN task t ON ta.task_id = t.task_id
    """).fetchall()

    project_stats = {}
    overdue_tasks = []
    blocked_count = 0
    done_count = 0
    urgent_tasks = []
    at_risk_tasks = []
    status_counts = {
        "todo": 0,
        "in_progress": 0,
        "blocked": 0,
        "done": 0,
    }
    quadrants = {
        "urgent_important": 0,
        "not_urgent_important": 0,
        "urgent_less_important": 0,
        "not_urgent_less_important": 0,
    }
    deadline_buckets = {
        "overdue": 0,
        "today": 0,
        "within_3_days": 0,
        "within_7_days": 0,
        "later": 0,
    }
    deadline_pressure_series = []
    quadrant_tasks = {
        "urgent_important": [],
        "not_urgent_important": [],
        "urgent_less_important": [],
        "not_urgent_less_important": [],
    }

    for row in task_rows:
        task = dict(row)
        urgency = round(float(task["urgency_score"] or 0), 2)
        importance = round(float(task["subjective_importance"] or 0), 2)
        deadline = parse_datetime_value(task["deadline"], naive_tz=HKT)
        is_done = task["status"] == "done"
        is_blocked = task["status"] == "blocked"
        is_overdue = bool(deadline and deadline < now and not is_done)
        is_urgent = urgency >= 0.7
        if task["status"] in status_counts:
            status_counts[task["status"]] += 1

        if is_done:
            done_count += 1
        if is_blocked:
            blocked_count += 1
        if is_overdue:
            overdue_tasks.append(task)
        if is_urgent:
            urgent_tasks.append(task)
        if deadline and not is_done and now <= deadline <= now + datetime.timedelta(days=3):
            at_risk_tasks.append(task)

        task_summary = {
            "task_id": task["task_id"],
            "title": task["title"],
            "project_title": task["project_title"],
            "subproject_title": task["subproject_title"],
            "urgency_score": urgency,
            "subjective_importance": importance,
            "deadline": to_hkt_iso(task["deadline"]),
            "status": task["status"],
        }

        if urgency >= 0.6 and importance >= 0.6:
            quadrants["urgent_important"] += 1
            quadrant_tasks["urgent_important"].append(task_summary)
        elif urgency < 0.6 and importance >= 0.6:
            quadrants["not_urgent_important"] += 1
            quadrant_tasks["not_urgent_important"].append(task_summary)
        elif urgency >= 0.6 and importance < 0.6:
            quadrants["urgent_less_important"] += 1
            quadrant_tasks["urgent_less_important"].append(task_summary)
        else:
            quadrants["not_urgent_less_important"] += 1
            quadrant_tasks["not_urgent_less_important"].append(task_summary)

        if deadline:
            if is_overdue:
                deadline_buckets["overdue"] += 1
            elif deadline.date() == now.date():
                deadline_buckets["today"] += 1
            elif deadline <= now + datetime.timedelta(days=3):
                deadline_buckets["within_3_days"] += 1
            elif deadline <= now + datetime.timedelta(days=7):
                deadline_buckets["within_7_days"] += 1
            else:
                deadline_buckets["later"] += 1

        stats = project_stats.setdefault(task["project_id"], {
            "project_id": task["project_id"],
            "title": task["project_title"],
            "task_count": 0,
            "done_count": 0,
            "overdue_count": 0,
            "blocked_count": 0,
            "urgent_count": 0,
        })
        stats["task_count"] += 1
        stats["done_count"] += int(is_done)
        stats["overdue_count"] += int(is_overdue)
        stats["blocked_count"] += int(is_blocked)
        stats["urgent_count"] += int(is_urgent)

    project_health = []
    project_risk_bands = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    for stats in project_stats.values():
        done_ratio = safe_ratio(stats["done_count"], stats["task_count"])
        health_score = round(max(0, min(
            100,
            100 - stats["overdue_count"] * 12 - stats["blocked_count"] * 8 - stats["urgent_count"] * 4 + done_ratio * 20
        )), 2)
        if health_score < 60:
            risk_band = "high"
        elif health_score < 80:
            risk_band = "medium"
        else:
            risk_band = "low"
        project_risk_bands[risk_band] += 1
        project_health.append({
            "project_id": stats["project_id"],
            "title": stats["title"],
            "health_score": health_score,
            "task_count": stats["task_count"],
            "done_ratio": done_ratio,
            "overdue_count": stats["overdue_count"],
            "blocked_count": stats["blocked_count"],
            "urgent_count": stats["urgent_count"],
            "risk_band": risk_band,
        })
    project_health.sort(key=lambda item: (item["health_score"], -item["overdue_count"], -item["urgent_count"], item["title"]))
    overdue_projects = [
        {
            "project_id": item["project_id"],
            "title": item["title"],
            "overdue_count": item["overdue_count"],
        }
        for item in project_health
        if item["overdue_count"] > 0
    ]
    project_risk_trend = [
        {
            "title": item["title"],
            "health_score": item["health_score"],
            "overdue_count": item["overdue_count"],
            "urgent_count": item["urgent_count"],
        }
        for item in project_health[:5]
    ]

    member_workload = []
    workload_pressure_counts = {
        "high": 0,
        "medium": 0,
        "light": 0,
    }
    member_index = {
        row["member_id"]: {
            "member_id": row["member_id"],
            "name": row["name"],
            "role": row["role"],
            "group_names": [name.strip() for name in (row["group_names"] or "").split(",") if name.strip()],
            "assigned_tasks": 0,
            "urgent_tasks": 0,
            "overdue_tasks": 0,
            "done_tasks": 0,
            "workload_score": 0.0,
            "pressure_band": "light",
        }
        for row in member_rows
    }
    for row in assignment_rows:
        member = member_index.get(row["member_id"])
        if not member:
            continue
        deadline = parse_datetime_value(row["deadline"], naive_tz=HKT)
        is_done = row["status"] == "done"
        is_overdue = bool(deadline and deadline < now and not is_done)
        is_urgent = float(row["urgency_score"] or 0) >= 0.7
        member["assigned_tasks"] += 1
        member["urgent_tasks"] += int(is_urgent)
        member["overdue_tasks"] += int(is_overdue)
        member["done_tasks"] += int(is_done)
    for member in member_index.values():
        workload_score = round(member["assigned_tasks"] + member["urgent_tasks"] * 1.5 + member["overdue_tasks"] * 2, 2)
        if workload_score >= 6:
            pressure_band = "high"
        elif workload_score >= 3:
            pressure_band = "medium"
        else:
            pressure_band = "light"
        member["workload_score"] = workload_score
        member["pressure_band"] = pressure_band
        workload_pressure_counts[pressure_band] += 1
    member_workload = sorted(
        member_index.values(),
        key=lambda item: (-item["workload_score"], -item["urgent_tasks"], -item["overdue_tasks"], -item["assigned_tasks"], item["name"])
    )

    pressure_counts_by_day = {}
    for day_offset in range(14):
        day = (now + datetime.timedelta(days=day_offset)).date()
        pressure_counts_by_day[day.isoformat()] = 0
    for row in task_rows:
        deadline = parse_datetime_value(row["deadline"], naive_tz=HKT)
        if not deadline:
            continue
        day_key = deadline.date().isoformat()
        if day_key in pressure_counts_by_day and row["status"] != "done":
            pressure_counts_by_day[day_key] += 1
    deadline_pressure_series = [
        {"date": day_key, "task_count": pressure_counts_by_day[day_key]}
        for day_key in sorted(pressure_counts_by_day.keys())
    ]

    top_risky_tasks = sorted([
        {
            "task_id": row["task_id"],
            "title": row["title"],
            "description": row["description"],
            "project_title": row["project_title"],
            "subproject_title": row["subproject_title"],
            "status": row["status"],
            "deadline": to_hkt_iso(row["deadline"]),
            "urgency_score": round(float(row["urgency_score"] or 0), 2),
        }
        for row in task_rows
    ], key=lambda item: (-item["urgency_score"], item["deadline"] or "9999-12-31T23:59:59+08:00", item["title"]))[:5]
    urgent_task_list = sorted([
        {
            "task_id": row["task_id"],
            "title": row["title"],
            "description": row["description"],
            "project_title": row["project_title"],
            "subproject_title": row["subproject_title"],
            "status": row["status"],
            "deadline": to_hkt_iso(row["deadline"]),
            "urgency_score": round(float(row["urgency_score"] or 0), 2),
        }
        for row in urgent_tasks
    ], key=lambda item: (-item["urgency_score"], item["deadline"] or "9999-12-31T23:59:59+08:00", item["title"]))[:8]
    for key in quadrant_tasks:
        quadrant_tasks[key] = sorted(
            quadrant_tasks[key],
            key=lambda item: (-item["urgency_score"], item["deadline"] or "9999-12-31T23:59:59+08:00", item["title"])
        )[:6]

    payload = {
        "generated_at": to_hkt_iso(now),
        "timezone": "Asia/Hong_Kong",
        "demo_mode": ANALYTICS_DEMO_MODE,
        "summary": {
            "total_projects": conn.execute("SELECT COUNT(*) FROM project").fetchone()[0],
            "total_subprojects": conn.execute("SELECT COUNT(*) FROM subproject").fetchone()[0],
            "total_tasks": len(task_rows),
            "overdue_tasks": len(overdue_tasks),
            "blocked_tasks": blocked_count,
            "done_tasks": done_count,
            "urgent_tasks": len(urgent_tasks),
            "at_risk_tasks": len(at_risk_tasks),
        },
        "project_health": project_health,
        "overdue_projects": overdue_projects,
        "project_risk_bands": project_risk_bands,
        "member_workload": member_workload,
        "quadrants": quadrants,
        "quadrant_tasks": quadrant_tasks,
        "status_counts": status_counts,
        "deadline_buckets": deadline_buckets,
        "deadline_pressure_series": deadline_pressure_series,
        "workload_pressure": workload_pressure_counts,
        "project_risk_trend": project_risk_trend,
        "urgent_task_list": urgent_task_list,
        "top_risky_tasks": top_risky_tasks,
    }

    snapshot = load_demo_analytics_snapshot()
    if snapshot:
        trend_fields = ("deadline_pressure_series", "workload_pressure", "project_risk_trend")
        for field in trend_fields:
            if field in snapshot:
                payload[field] = snapshot[field]
        payload["trend_source"] = "mock_snapshot"
        payload["snapshot_generated_at"] = snapshot.get("generated_at")
    else:
        payload["trend_source"] = "live"
        payload["snapshot_generated_at"] = None

    return payload

# ==========================================
# 4. ROUTES
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")

# ---------- AUTH ----------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    student_id = (data.get("student_id") or "").strip().lower()
    password = data.get("password") or ""

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM member WHERE student_id = ?",
            (student_id,)
        ).fetchone()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["member_id"]
        session["student_id"] = user["student_id"]
        session["name"] = user["name"]
        session["role"] = user["role"]

        return jsonify({
            "status": "success",
            "user": {
                "id": user["member_id"],
                "student_id": user["student_id"],
                "name": user["name"],
                "role": user["role"]
            }
        })

    return jsonify({"status": "error", "message": "Invalid student ID or password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})

@app.route("/api/session", methods=["GET"])
def get_session():
    if "user_id" in session:
        return jsonify({
            "logged_in": True,
            "user": {
                "id": session["user_id"],
                "student_id": session["student_id"],
                "name": session["name"],
                "role": session["role"]
            }
        })
    return jsonify({"logged_in": False})

# ---------- MEMBER ----------
@app.route("/api/members", methods=["GET", "POST"])
def handle_members():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        if not is_admin():
            return jsonify({"error": "Only admin can create members"}), 403

        data = request.json or {}
        student_id = (data.get("student_id") or "").strip().lower()
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = (data.get("role") or "member").strip().lower()
        group_ids = data.get("group_ids", [])

        if not student_id or not name or not email or not password:
            return jsonify({"error": "Student ID, name, email, and password are required"}), 400
        if role not in MEMBER_ROLES:
            return jsonify({"error": "Invalid role"}), 400

        try:
            group_ids = sorted({int(group_id) for group_id in group_ids})
        except (TypeError, ValueError):
            return jsonify({"error": "group_ids must be integer array"}), 400

        try:
            with get_db_connection() as conn:
                if group_ids:
                    placeholders = ",".join("?" for _ in group_ids)
                    valid_group_ids = {
                        row["group_id"]
                        for row in conn.execute(
                            f"SELECT group_id FROM team_group WHERE group_id IN ({placeholders})",
                            group_ids
                        ).fetchall()
                    }
                    if len(valid_group_ids) != len(group_ids):
                        return jsonify({"error": "One or more groups do not exist"}), 400

                cursor = conn.execute("""
                    INSERT INTO member (student_id, password_hash, name, email, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, generate_password_hash(password), name, email, role, hkt_db_timestamp()))
                member_id = cursor.lastrowid

                for group_id in group_ids:
                    conn.execute("""
                        INSERT INTO member_group (member_id, group_id, joined_at)
                        VALUES (?, ?, ?)
                    """, (member_id, group_id, hkt_db_timestamp()))

                conn.commit()
        except sqlite3.IntegrityError as exc:
            message = str(exc).lower()
            if "student_id" in message:
                return jsonify({"error": "Student ID already exists"}), 400
            if "email" in message:
                return jsonify({"error": "Email already exists"}), 400
            return jsonify({"error": "Failed to create member"}), 400

        return jsonify({"status": "success", "member_id": member_id}), 201

    with get_db_connection() as conn:
        members = conn.execute("""
            SELECT
                m.member_id, m.student_id, m.name, m.email, m.role, m.created_at,
                GROUP_CONCAT(g.group_name, ', ') AS groups
            FROM member m
            LEFT JOIN member_group mg ON m.member_id = mg.member_id
            LEFT JOIN team_group g ON mg.group_id = g.group_id
            GROUP BY m.member_id
            ORDER BY m.member_id ASC
        """).fetchall()

    return jsonify([dict(m) for m in members])

@app.route("/api/members/<int:member_id>", methods=["PUT", "DELETE"])
def manage_member(member_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "DELETE":
        if not is_admin():
            return jsonify({"error": "Only admin can delete members"}), 403
        if current_user_id() == member_id:
            return jsonify({"error": "You cannot delete your own account"}), 400

        with get_db_connection() as conn:
            target = conn.execute(
                "SELECT role FROM member WHERE member_id = ?",
                (member_id,)
            ).fetchone()

            if not target:
                return jsonify({"error": "Member not found"}), 404

            if target["role"] == "admin":
                admin_count = conn.execute(
                    "SELECT COUNT(*) FROM member WHERE role = 'admin'"
                ).fetchone()[0]
                if admin_count <= 1:
                    return jsonify({"error": "Cannot delete the last admin"}), 400

            conn.execute("DELETE FROM member WHERE member_id = ?", (member_id,))
            conn.commit()

        return jsonify({"status": "success"})

    if not can_edit_member(member_id):
        return jsonify({"error": "Forbidden"}), 403

    data = request.json or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    try:
        with get_db_connection() as conn:
            existing = conn.execute(
                "SELECT member_id FROM member WHERE member_id = ?",
                (member_id,)
            ).fetchone()
            if not existing:
                return jsonify({"error": "Member not found"}), 404

            if password:
                conn.execute("""
                    UPDATE member
                    SET name = ?, email = ?, password_hash = ?
                    WHERE member_id = ?
                """, (name, email, generate_password_hash(password), member_id))
            else:
                conn.execute("""
                    UPDATE member
                    SET name = ?, email = ?
                    WHERE member_id = ?
                """, (name, email, member_id))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400

    if current_user_id() == member_id:
        session["name"] = name

    return jsonify({"status": "success"})

# ---------- GROUPS ----------
@app.route("/api/groups", methods=["GET", "POST"])
def handle_groups():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        if not is_admin():
            return jsonify({"error": "Only admin can create groups"}), 403

        data = request.json or {}
        group_name = (data.get("group_name") or "").strip()
        description = (data.get("description") or "").strip()

        if not group_name:
            return jsonify({"error": "group_name is required"}), 400

        try:
            with get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO team_group (group_name, description, created_at)
                    VALUES (?, ?, ?)
                """, (group_name, description, hkt_db_timestamp()))
                conn.commit()
            return jsonify({"status": "success"})
        except sqlite3.IntegrityError:
            return jsonify({"error": "Group name already exists"}), 400

    with get_db_connection() as conn:
        groups = conn.execute("""
            SELECT
                g.group_id, g.group_name, g.description, g.created_at,
                COUNT(mg.member_id) AS member_count
            FROM team_group g
            LEFT JOIN member_group mg ON g.group_id = mg.group_id
            GROUP BY g.group_id
            ORDER BY g.group_name ASC
        """).fetchall()
    return jsonify([dict(g) for g in groups])

@app.route("/api/groups/<int:group_id>", methods=["PUT"])
def update_group(group_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_admin():
        return jsonify({"error": "Only admin can update groups"}), 403

    data = request.json or {}
    description = (data.get("description") or "").strip()

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT group_id FROM team_group WHERE group_id = ?",
            (group_id,)
        ).fetchone()
        if not existing:
            return jsonify({"error": "Group not found"}), 404

        conn.execute("""
            UPDATE team_group
            SET description = ?
            WHERE group_id = ?
        """, (description, group_id))
        conn.commit()

    return jsonify({"status": "success"})

@app.route("/api/groups/<int:group_id>/members", methods=["GET", "PUT"])
def update_group_members(group_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    with get_db_connection() as conn:
        existing_group = conn.execute(
            "SELECT group_id FROM team_group WHERE group_id = ?",
            (group_id,)
        ).fetchone()
        if not existing_group:
            return jsonify({"error": "Group not found"}), 404

        if request.method == "GET":
            rows = conn.execute("""
                SELECT member_id
                FROM member_group
                WHERE group_id = ?
                ORDER BY member_id ASC
            """, (group_id,)).fetchall()
            return jsonify({"member_ids": [row["member_id"] for row in rows]})

        if not is_admin():
            return jsonify({"error": "Only admin can update group membership"}), 403

        data = request.json or {}
        member_ids = data.get("member_ids", [])

        try:
            member_ids = sorted({int(x) for x in member_ids})
        except Exception:
            return jsonify({"error": "member_ids must be integer array"}), 400

        if member_ids:
            placeholders = ",".join("?" for _ in member_ids)
            valid_member_ids = {
                row["member_id"]
                for row in conn.execute(
                    f"SELECT member_id FROM member WHERE member_id IN ({placeholders})",
                    member_ids
                ).fetchall()
            }
            if len(valid_member_ids) != len(member_ids):
                return jsonify({"error": "One or more members do not exist"}), 400

            conn.execute("DELETE FROM member_group WHERE group_id = ?", (group_id,))
            for mid in member_ids:
                conn.execute("""
                INSERT INTO member_group (member_id, group_id, joined_at)
                VALUES (?, ?, ?)
            """, (mid, group_id, hkt_db_timestamp()))
        conn.commit()

    return jsonify({"status": "success"})

# ---------- PROJECT ----------
@app.route("/api/projects", methods=["GET", "POST"])
def handle_projects():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        if not can_manage_structure():
            return jsonify({"error": "Forbidden"}), 403

        data = request.json or {}
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        owner_member_id = data.get("owner_member_id")

        if not title:
            return jsonify({"error": "Project title is required"}), 400

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO project (title, description, owner_member_id, created_by, status, created_at)
                VALUES (?, ?, ?, ?, 'planning', ?)
            """, (title, description, owner_member_id, current_user_id(), hkt_db_timestamp()))
            conn.commit()

        return jsonify({"status": "success"})

    with get_db_connection() as conn:
        projects = conn.execute("""
            SELECT
                p.project_id, p.title, p.description, p.status,
                p.start_date, p.end_date, p.created_at,
                owner.name AS owner_name,
                COUNT(sp.subproject_id) AS subproject_count
            FROM project p
            LEFT JOIN member owner ON p.owner_member_id = owner.member_id
            LEFT JOIN subproject sp ON p.project_id = sp.project_id
            GROUP BY p.project_id
            ORDER BY p.project_id DESC
        """).fetchall()

    return jsonify([dict(p) for p in projects])

# ---------- SUBPROJECT ----------
@app.route("/api/subprojects", methods=["GET", "POST"])
def handle_subprojects():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        if not can_manage_structure():
            return jsonify({"error": "Forbidden"}), 403

        data = request.json or {}
        project_id = data.get("project_id")
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        owner_member_id = data.get("owner_member_id")

        if not project_id or not title:
            return jsonify({"error": "project_id and title are required"}), 400

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO subproject (project_id, title, description, owner_member_id, created_by, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'planning', ?)
            """, (project_id, title, description, owner_member_id, current_user_id(), hkt_db_timestamp()))
            conn.commit()

        return jsonify({"status": "success"})

    with get_db_connection() as conn:
        subprojects = conn.execute("""
            SELECT
                sp.subproject_id, sp.project_id, sp.title, sp.description, sp.status,
                p.title AS project_title,
                owner.name AS owner_name
            FROM subproject sp
            JOIN project p ON sp.project_id = p.project_id
            LEFT JOIN member owner ON sp.owner_member_id = owner.member_id
            ORDER BY sp.subproject_id DESC
        """).fetchall()

    return jsonify([dict(s) for s in subprojects])

# ---------- TASK ----------
@app.route("/api/tasks", methods=["GET", "POST"])
def handle_tasks():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        if not can_manage_structure():
            return jsonify({"error": "Forbidden"}), 403

        data = request.json or {}
        subproject_id = data.get("subproject_id")
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        deadline = data.get("deadline")
        importance = data.get("importance", 0.5)
        assigned_member_ids = data.get("assigned_member_ids", [])

        if not subproject_id or not title:
            return jsonify({"error": "subproject_id and title are required"}), 400

        try:
            assigned_member_ids = [int(x) for x in assigned_member_ids]
        except Exception:
            return jsonify({"error": "assigned_member_ids must be integer array"}), 400

        normalized_deadline = normalize_deadline_value(deadline)
        u_score = calculate_urgency(deadline, importance)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO task (
                    subproject_id, title, description, deadline,
                    subjective_importance, urgency_score, created_by, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subproject_id, title, description, normalized_deadline,
                importance, u_score, current_user_id(), hkt_db_timestamp(), hkt_db_timestamp()
            ))
            task_id = cursor.lastrowid

            for member_id in assigned_member_ids:
                cursor.execute("""
                    INSERT INTO task_assignment (task_id, member_id, responsibility_type, assigned_at)
                    VALUES (?, ?, 'owner', ?)
                """, (task_id, member_id, hkt_db_timestamp()))

            conn.commit()

        return jsonify({"status": "success", "task_id": task_id})

    with get_db_connection() as conn:
        tasks = conn.execute("""
            SELECT
                t.task_id, t.title, t.description, t.status, t.deadline,
                t.subjective_importance, t.urgency_score,
                sp.title AS subproject_title,
                p.title AS project_title,
                GROUP_CONCAT(m.name, ', ') AS assignee_names
            FROM task t
            JOIN subproject sp ON t.subproject_id = sp.subproject_id
            JOIN project p ON sp.project_id = p.project_id
            LEFT JOIN task_assignment ta ON t.task_id = ta.task_id
            LEFT JOIN member m ON ta.member_id = m.member_id
            GROUP BY t.task_id
            ORDER BY t.deadline IS NULL, t.deadline ASC, t.task_id DESC
        """).fetchall()

    return jsonify([dict(t) for t in tasks])

@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_admin():
        return jsonify({"error": "Only admin can edit tasks"}), 403

    data = request.json or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    urgency = data.get("urgency", 0.5)

    if not title:
        return jsonify({"error": "Task title is required"}), 400

    try:
        urgency = float(urgency)
    except (TypeError, ValueError):
        return jsonify({"error": "urgency must be a number"}), 400

    if not 0 <= urgency <= 1:
        return jsonify({"error": "urgency must be between 0 and 1"}), 400

    with get_db_connection() as conn:
        task = conn.execute(
            "SELECT task_id FROM task WHERE task_id = ?",
            (task_id,)
        ).fetchone()
        if not task:
            return jsonify({"error": "Task not found"}), 404

        conn.execute("""
            UPDATE task
            SET title = ?,
                description = ?,
                urgency_score = ?,
                updated_at = ?
            WHERE task_id = ?
        """, (title, description, round(urgency, 2), hkt_db_timestamp(), task_id))
        conn.commit()

    return jsonify({"status": "success"})

# ---------- ANALYTICS ----------
@app.route("/api/analytics/summary", methods=["GET"])
def analytics_summary():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if current_role() not in ["admin", "leader"]:
        return jsonify({"error": "Only admin and leader can access analytics"}), 403

    with get_db_connection() as conn:
        payload = build_analytics_summary(conn)

    return jsonify(payload)

# ==========================================
# 6. EXECUTION
# ==========================================

def run_app():
    try:
        from google.colab.output import serve_kernel_port_as_iframe
        print("Detected Google Colab environment.")
        threading.Thread(
            target=lambda: app.run(port=5000, host="0.0.0.0", debug=False, use_reloader=False)
        ).start()
        serve_kernel_port_as_iframe(5000)
    except ImportError:
        print("Detected Terminal environment. Starting at http://127.0.0.1:5000")
        app.run(port=5000, debug=True)

if __name__ == "__main__":
    run_app()
