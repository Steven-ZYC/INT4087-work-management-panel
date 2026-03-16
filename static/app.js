let currentUser = null;
let allMembers = [];
let allProjects = [];
let allSubprojects = [];
let allGroups = [];
let allTasks = [];
let analyticsSummary = null;
let currentAnalyticsTab = "overview";

function encodeInlineValue(value) {
    return encodeURIComponent(value ?? "");
}

function decodeInlineValue(value) {
    return decodeURIComponent(value || "");
}

function closeModal(id) {
    document.getElementById(id).classList.add("hidden");
}

function openTaskModal() {
    document.getElementById("task-modal").classList.remove("hidden");
}

function updateNewTaskUrgencyLabel(value) {
    document.getElementById("ti-value").innerText = Number(value).toFixed(2);
}

function updateTaskUrgencyLabel(value) {
    document.getElementById("et-importance-value").innerText = Number(value).toFixed(2);
}

function getUrgencyTheme(score) {
    if (score >= 0.85) {
        return {
            card: "bg-rose-100 border-rose-400",
            accent: "border-l-rose-600",
            badge: "bg-rose-600 text-white border-rose-700"
        };
    }
    if (score >= 0.7) {
        return {
            card: "bg-orange-50 border-orange-300",
            accent: "border-l-orange-500",
            badge: "bg-orange-500 text-white border-orange-600"
        };
    }
    if (score >= 0.5) {
        return {
            card: "bg-amber-50 border-amber-200",
            accent: "border-l-amber-400",
            badge: "bg-amber-100 text-amber-900 border-amber-200"
        };
    }
    return {
        card: "bg-white border-stone-200",
        accent: "border-l-stone-300",
        badge: "bg-[var(--soft)] text-[var(--text)] border-[var(--border)]"
    };
}

function renderQuadrant(containerId, tasks) {
    const container = document.getElementById(containerId);
    if (!tasks.length) {
        container.innerHTML = '<div class="text-sm text-[var(--muted)]">No tasks in this quadrant.</div>';
        return;
    }

    container.innerHTML = tasks.map((task) => `
        <div class="bg-white border rounded-xl px-3 py-2">
            <div class="font-medium text-sm">${task.title}</div>
            <div class="text-xs text-[var(--muted)] mt-1">${task.project_title} / ${task.subproject_title}</div>
            <div class="text-xs text-[var(--subtle)] mt-1">Urgency: ${Number(task.urgency_score).toFixed(2)} · Importance: ${Number(task.subjective_importance ?? 0.5).toFixed(2)}</div>
        </div>
    `).join("");
}

function renderUrgentTasks(tasks) {
    const container = document.getElementById("todo-list");
    if (!tasks.length) {
        container.innerHTML = '<div class="text-sm text-[var(--muted)]">No urgent tasks right now.</div>';
        return;
    }

    container.innerHTML = tasks.map((task) => {
        const theme = getUrgencyTheme(Number(task.urgency_score));
        return `
            <div class="${theme.card} p-4 rounded-2xl border-l-4 ${theme.accent} border shadow-sm">
                <div class="flex justify-between items-start gap-3">
                    <div>
                        <div class="flex items-start gap-3">
                            <span class="font-semibold block">${task.title}</span>
                            ${currentUser.role === "admin"
                                ? `<button onclick="openEditTask(${task.task_id})" class="text-[var(--accent)] hover:underline text-sm whitespace-nowrap">Edit</button>`
                                : ""}
                        </div>
                        ${task.description ? `<span class="text-sm text-[var(--muted)] block mt-2">${task.description}</span>` : ""}
                        <span class="text-xs text-[var(--muted)] block mt-1">${task.project_title} / ${task.subproject_title}</span>
                        <span class="text-xs text-[var(--subtle)] block mt-1">Deadline: ${formatHktDateTime(task.deadline)}</span>
                    </div>
                    <span class="text-xs font-mono ${theme.badge} p-2 rounded-xl border whitespace-nowrap">
                        ${Number(task.urgency_score).toFixed(2)}
                    </span>
                </div>
            </div>
        `;
    }).join("");
}

function renderDashboardAnalytics() {
    if (!analyticsSummary) {
        document.getElementById("dashboard-overdue-count").innerText = "0";
        document.getElementById("dashboard-overdue-meta").innerText = "Analytics unavailable";
        document.getElementById("dashboard-generated-at").innerText = "Analytics unavailable";
        const trendMeta = document.getElementById("analytics-trend-meta");
        if (trendMeta) trendMeta.innerText = "Trend source unavailable";
        document.getElementById("dashboard-overdue-projects").innerHTML = '<div class="text-sm text-[var(--muted)]">No analytics data available.</div>';
        renderUrgentTasks([]);
        renderQuadrant("quadrant-urgent-important", []);
        renderQuadrant("quadrant-not-urgent-important", []);
        renderQuadrant("quadrant-urgent-less-important", []);
        renderQuadrant("quadrant-not-urgent-less-important", []);
        return;
    }

    const summary = analyticsSummary.summary || {};
    const overdueProjects = analyticsSummary.overdue_projects || [];
    const urgentTaskList = analyticsSummary.urgent_task_list || [];
    const quadrantTasks = analyticsSummary.quadrant_tasks || {};

    document.getElementById("dashboard-generated-at").innerText = `Analytics generated ${formatHktDateTime(analyticsSummary.generated_at)}`;
    document.getElementById("dashboard-overdue-count").innerText = overdueProjects.length;
    document.getElementById("dashboard-overdue-meta").innerText = `${summary.overdue_tasks ?? 0} overdue tasks`;
    document.getElementById("dashboard-overdue-projects").innerHTML = overdueProjects.length
        ? overdueProjects.map((project) => `
            <span class="px-3 py-2 rounded-full bg-rose-100 text-rose-900 border border-rose-200 text-sm">
                ${project.title} · ${project.overdue_count}
            </span>
        `).join("")
        : '<div class="text-sm text-[var(--muted)]">No overdue projects right now.</div>';

    renderUrgentTasks(urgentTaskList);
    renderQuadrant("quadrant-urgent-important", quadrantTasks.urgent_important || []);
    renderQuadrant("quadrant-not-urgent-important", quadrantTasks.not_urgent_important || []);
    renderQuadrant("quadrant-urgent-less-important", quadrantTasks.urgent_less_important || []);
    renderQuadrant("quadrant-not-urgent-less-important", quadrantTasks.not_urgent_less_important || []);
}

function openProjectModal() {
    document.getElementById("project-modal").classList.remove("hidden");
}

function openSubprojectModal() {
    document.getElementById("subproject-modal").classList.remove("hidden");
}

function openGroupModal() {
    document.getElementById("group-name").value = "";
    document.getElementById("group-desc").value = "";
    document.getElementById("group-modal").classList.remove("hidden");
}

function populateNewMemberGroups() {
    const groupBox = document.getElementById("nm-groups");
    if (!groupBox) return;

    if (!allGroups.length) {
        groupBox.innerHTML = '<div class="text-sm text-[var(--muted)]">No groups available yet.</div>';
        return;
    }

    groupBox.innerHTML = allGroups.map((g) => `
        <label class="flex items-center space-x-2 bg-white border rounded-xl px-3 py-2">
            <input type="checkbox" class="new-member-group-checkbox" value="${g.group_id}">
            <span class="text-sm">${g.group_name}</span>
        </label>
    `).join("");
}

function openMemberModal() {
    document.getElementById("nm-student-id").value = "";
    document.getElementById("nm-name").value = "";
    document.getElementById("nm-email").value = "";
    document.getElementById("nm-role").value = "member";
    document.getElementById("nm-pass").value = "";
    populateNewMemberGroups();
    document.getElementById("member-modal").classList.remove("hidden");
}

function show(v) {
    document.getElementById("dashboard-view").classList.toggle("hidden", v !== "dashboard");
    document.getElementById("projects-view").classList.toggle("hidden", v !== "projects");
    document.getElementById("analytics-view").classList.toggle("hidden", v !== "analytics");
    document.getElementById("groups-view").classList.toggle("hidden", v !== "groups");
    document.getElementById("members-view").classList.toggle("hidden", v !== "members");
    if (v === "analytics") {
        showAnalyticsTab(currentAnalyticsTab);
    }
}

async function checkSession() {
    const res = await fetch("/api/session");
    const data = await res.json();
    if (data.logged_in) {
        currentUser = data.user;
        document.getElementById("user-info").innerHTML =
            `<div class="font-medium">${currentUser.name}</div>
             <div class="text-[var(--muted)]">${currentUser.student_id}</div>
             <div class="text-[var(--subtle)] mt-1">${currentUser.role}</div>`;
        document.getElementById("login-view").classList.add("hidden");
        document.getElementById("app-view").classList.remove("hidden");
        await initApp();
    } else {
        document.getElementById("login-view").classList.remove("hidden");
        document.getElementById("app-view").classList.add("hidden");
    }
}

async function login() {
    const studentId = document.getElementById("l-student-id").value.trim().toLowerCase();
    const p = document.getElementById("l-pass").value;

    const res = await fetch("/api/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({student_id: studentId, password: p})
    });

    const data = await res.json();
    if (res.ok) {
        document.getElementById("login-error").classList.add("hidden");
        await checkSession();
    } else {
        document.getElementById("login-error").innerText = data.message || "Login failed";
        document.getElementById("login-error").classList.remove("hidden");
    }
}

async function logout() {
    await fetch("/api/logout", {method: "POST"});
    currentUser = null;
    document.getElementById("l-student-id").value = "";
    document.getElementById("l-pass").value = "";
    await checkSession();
}

async function initApp() {
    await loadMembers();
    await loadGroups();
    await loadProjects();
    await loadSubprojects();
    await loadTasks();
    await loadAnalytics();
    populateOwnerSelects();
    populateProjectSelects();
    populateSubprojectOptions();
}

function renderAnalyticsEmptyState(containerId, message) {
    document.getElementById(containerId).innerHTML = `<div class="text-sm text-[var(--muted)]">${message}</div>`;
}

function formatHktDateTime(value) {
    if (!value) return "No timestamp";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("en-HK", {
        timeZone: "Asia/Hong_Kong",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    }).format(date) + " HKT";
}

function healthTone(score) {
    if (score >= 80) return "text-emerald-700 bg-emerald-50 border-emerald-200";
    if (score >= 60) return "text-amber-700 bg-amber-50 border-amber-200";
    return "text-rose-700 bg-rose-50 border-rose-200";
}

function pressureTone(band) {
    if (band === "high") return "bg-rose-50 border-rose-200 text-rose-700";
    if (band === "medium") return "bg-amber-50 border-amber-200 text-amber-700";
    return "bg-emerald-50 border-emerald-200 text-emerald-700";
}

function formatHktDate(value) {
    if (!value) return "No date";
    const date = new Date(`${value}T00:00:00+08:00`);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("en-HK", {
        timeZone: "Asia/Hong_Kong",
        month: "2-digit",
        day: "2-digit"
    }).format(date);
}

function showAnalyticsTab(tab) {
    currentAnalyticsTab = tab;
    const tabs = ["overview", "risk", "pressure", "trends", "details"];
    tabs.forEach((name) => {
        const panel = document.getElementById(`analytics-panel-${name}`);
        const button = document.getElementById(`analytics-tab-${name}`);
        if (panel) panel.classList.toggle("hidden", name !== tab);
        if (button) {
            button.classList.toggle("analytics-subnav-btn-active", name === tab);
        }
    });
}

async function loadAnalytics() {
    const canViewAnalytics = ["admin", "leader"].includes(currentUser.role);
    const navButton = document.getElementById("analytics-nav-btn");
    const accessNote = document.getElementById("analytics-access-note");
    const content = document.getElementById("analytics-content");

    navButton.classList.toggle("hidden", !canViewAnalytics);
    accessNote.classList.toggle("hidden", canViewAnalytics);
    content.classList.toggle("hidden", !canViewAnalytics);

    if (!canViewAnalytics) {
        analyticsSummary = null;
        renderDashboardAnalytics();
        return;
    }

    const res = await fetch("/api/analytics/summary");
    const data = await res.json();
    if (!res.ok) {
        analyticsSummary = null;
        renderDashboardAnalytics();
        renderAnalyticsEmptyState("analytics-project-health", data.error || "Failed to load analytics");
        renderAnalyticsEmptyState("analytics-member-workload", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-deadline-buckets", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-status-distribution", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-project-risk-bands", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-deadline-pressure-series", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-workload-pressure", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-project-risk-trend", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-top-risky-tasks", "Analytics is unavailable.");
        renderAnalyticsEmptyState("analytics-quadrants", "Analytics is unavailable.");
        return;
    }

    analyticsSummary = data;
    renderDashboardAnalytics();
    const summary = data.summary || {};
    const projectHealth = data.project_health || [];
    const memberWorkload = data.member_workload || [];
    const deadlineBuckets = data.deadline_buckets || {};
    const deadlinePressureSeries = data.deadline_pressure_series || [];
    const projectRiskBands = data.project_risk_bands || {};
    const statusCounts = data.status_counts || {};
    const workloadPressure = data.workload_pressure || {};
    const projectRiskTrend = data.project_risk_trend || [];
    const topRiskyTasks = data.top_risky_tasks || [];
    const quadrants = data.quadrants || {};
    const trendMeta = document.getElementById("analytics-trend-meta");
    const snapshotGeneratedAt = data.snapshot_generated_at ? formatHktDateTime(data.snapshot_generated_at) : null;
    if (trendMeta) {
        trendMeta.innerText = data.trend_source === "mock_snapshot"
            ? `Trend source: demo snapshot${snapshotGeneratedAt ? ` · snapshot ${snapshotGeneratedAt}` : ""}`
            : "Trend source: live analytics";
    }

    document.getElementById("analytics-total-projects").innerText = summary.total_projects ?? 0;
    document.getElementById("analytics-total-tasks").innerText = summary.total_tasks ?? 0;
    document.getElementById("analytics-overdue-tasks").innerText = summary.overdue_tasks ?? 0;
    document.getElementById("analytics-urgent-tasks").innerText = summary.urgent_tasks ?? 0;
    document.getElementById("analytics-at-risk-tasks").innerText = `${summary.at_risk_tasks ?? 0} at risk`;
    document.getElementById("analytics-done-tasks").innerText = `${summary.done_tasks ?? 0} done`;
    document.getElementById("analytics-blocked-tasks").innerText = `${summary.blocked_tasks ?? 0} blocked`;
    document.getElementById("analytics-generated-at").innerText = `Generated ${formatHktDateTime(data.generated_at)}`;

    document.getElementById("analytics-project-health").innerHTML = projectHealth.length
        ? projectHealth.map((project) => `
            <div class="bg-white border rounded-2xl p-4">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <div class="font-medium">${project.title}</div>
                        <div class="text-xs text-[var(--muted)] mt-2">
                            ${project.task_count} tasks · ${(Number(project.done_ratio || 0) * 100).toFixed(0)}% done
                        </div>
                        <div class="text-xs text-[var(--subtle)] mt-1">
                            ${project.overdue_count} overdue · ${project.blocked_count} blocked · ${project.urgent_count} urgent
                        </div>
                    </div>
                    <div class="analytics-pill ${healthTone(Number(project.health_score || 0))}">
                        ${Number(project.health_score || 0).toFixed(0)}
                    </div>
                </div>
            </div>
        `).join("")
        : '<div class="text-sm text-[var(--muted)]">No project health data available.</div>';

    document.getElementById("analytics-member-workload").innerHTML = memberWorkload.length
        ? memberWorkload.map((member) => `
            <div class="bg-white border rounded-2xl p-4">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <div class="font-medium">${member.name}</div>
                        <div class="text-xs text-[var(--muted)] mt-2">${member.role} · ${(member.group_names || []).join(", ") || "No groups"}</div>
                    </div>
                    <div class="text-right text-xs text-[var(--subtle)]">
                        <div>${member.assigned_tasks} assigned</div>
                        <div class="mt-1">${member.urgent_tasks} urgent · ${member.overdue_tasks} overdue</div>
                        <div class="mt-1">${member.pressure_band} pressure · score ${Number(member.workload_score || 0).toFixed(2)}</div>
                    </div>
                </div>
            </div>
        `).join("")
        : '<div class="text-sm text-[var(--muted)]">No member workload data available.</div>';

    document.getElementById("analytics-deadline-buckets").innerHTML = [
        ["Overdue", deadlineBuckets.overdue ?? 0, "bg-rose-50 border-rose-200 text-rose-700"],
        ["Today", deadlineBuckets.today ?? 0, "bg-orange-50 border-orange-200 text-orange-700"],
        ["Within 3 Days", deadlineBuckets.within_3_days ?? 0, "bg-amber-50 border-amber-200 text-amber-700"],
        ["Within 7 Days", deadlineBuckets.within_7_days ?? 0, "bg-sky-50 border-sky-200 text-sky-700"],
        ["Later", deadlineBuckets.later ?? 0, "bg-stone-50 border-stone-200 text-stone-700"]
    ].map(([label, count, tone]) => `
        <div class="analytics-row ${tone}">
            <span>${label}</span>
            <span class="font-semibold">${count}</span>
        </div>
    `).join("");

    document.getElementById("analytics-status-distribution").innerHTML = [
        ["Todo", statusCounts.todo ?? 0, "bg-stone-50 border-stone-200 text-stone-700"],
        ["In Progress", statusCounts.in_progress ?? 0, "bg-sky-50 border-sky-200 text-sky-700"],
        ["Blocked", statusCounts.blocked ?? 0, "bg-rose-50 border-rose-200 text-rose-700"],
        ["Done", statusCounts.done ?? 0, "bg-emerald-50 border-emerald-200 text-emerald-700"]
    ].map(([label, count, tone]) => `
        <div class="analytics-row ${tone}">
            <span>${label}</span>
            <span class="font-semibold">${count}</span>
        </div>
    `).join("");

    document.getElementById("analytics-project-risk-bands").innerHTML = [
        ["High Risk", projectRiskBands.high ?? 0, "bg-rose-50 border-rose-200 text-rose-700"],
        ["Medium Risk", projectRiskBands.medium ?? 0, "bg-amber-50 border-amber-200 text-amber-700"],
        ["Low Risk", projectRiskBands.low ?? 0, "bg-emerald-50 border-emerald-200 text-emerald-700"]
    ].map(([label, count, tone]) => `
        <div class="analytics-row ${tone}">
            <span>${label}</span>
            <span class="font-semibold">${count}</span>
        </div>
    `).join("");

    document.getElementById("analytics-deadline-pressure-series").innerHTML = deadlinePressureSeries.length
        ? deadlinePressureSeries.map((point) => `
            <div class="analytics-row ${point.task_count >= 3 ? "bg-rose-50 border-rose-200 text-rose-700" : point.task_count >= 1 ? "bg-amber-50 border-amber-200 text-amber-700" : "bg-stone-50 border-stone-200 text-stone-700"}">
                <span>${formatHktDate(point.date)}</span>
                <span class="font-semibold">${point.task_count}</span>
            </div>
        `).join("")
        : '<div class="text-sm text-[var(--muted)]">No deadline pressure data available.</div>';

    document.getElementById("analytics-workload-pressure").innerHTML = [
        ["High", workloadPressure.high ?? 0, "high"],
        ["Medium", workloadPressure.medium ?? 0, "medium"],
        ["Light", workloadPressure.light ?? 0, "light"]
    ].map(([label, count, band]) => `
        <div class="analytics-row ${pressureTone(band)}">
            <span>${label}</span>
            <span class="font-semibold">${count}</span>
        </div>
    `).join("");

    document.getElementById("analytics-project-risk-trend").innerHTML = projectRiskTrend.length
        ? projectRiskTrend.map((project) => `
            <div class="analytics-row ${healthTone(Number(project.health_score || 0))}">
                <span>${project.title}</span>
                <span class="font-semibold">
                    ${Number(project.health_score || 0).toFixed(0)}
                    <span class="text-xs ml-2">${project.overdue_count ?? 0} overdue · ${project.urgent_count ?? 0} urgent</span>
                </span>
            </div>
        `).join("")
        : '<div class="text-sm text-[var(--muted)]">No project risk trend data available.</div>';

    document.getElementById("analytics-top-risky-tasks").innerHTML = topRiskyTasks.length
        ? topRiskyTasks.map((task) => `
            <div class="bg-white border rounded-2xl p-4">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <div class="font-medium">${task.title}</div>
                        <div class="text-xs text-[var(--muted)] mt-2">${task.project_title} / ${task.subproject_title}</div>
                        <div class="text-xs text-[var(--subtle)] mt-1">Deadline: ${formatHktDateTime(task.deadline)}</div>
                    </div>
                    <div class="analytics-pill bg-rose-50 border-rose-200 text-rose-700">
                        ${Number(task.urgency_score || 0).toFixed(2)}
                    </div>
                </div>
            </div>
        `).join("")
        : '<div class="text-sm text-[var(--muted)]">No risky tasks identified.</div>';

    document.getElementById("analytics-quadrants").innerHTML = [
        ["Urgent + Important", quadrants.urgent_important ?? 0, "bg-rose-50 border-rose-200"],
        ["Not Urgent + Important", quadrants.not_urgent_important ?? 0, "bg-amber-50 border-amber-200"],
        ["Urgent + Less Important", quadrants.urgent_less_important ?? 0, "bg-sky-50 border-sky-200"],
        ["Not Urgent + Less Important", quadrants.not_urgent_less_important ?? 0, "bg-stone-50 border-stone-200"]
    ].map(([label, count, tone]) => `
        <div class="border rounded-2xl p-4 ${tone}">
            <div class="text-sm text-[var(--muted)]">${label}</div>
            <div class="text-3xl font-lora font-semibold mt-2">${count}</div>
        </div>
    `).join("");
}

async function loadMembers() {
    const res = await fetch("/api/members");
    allMembers = await res.json();
    document.getElementById("new-member-btn").classList.toggle("hidden", currentUser.role !== "admin");

    document.getElementById("ta-list").innerHTML = allMembers.map((m) => `
        <label class="flex items-center space-x-2 bg-white border rounded-xl px-3 py-2">
            <input type="checkbox" class="assign-member-checkbox" value="${m.member_id}">
            <span class="text-sm">${m.name} (${m.student_id}, ${m.role})</span>
        </label>
    `).join("");

    const tbody = document.getElementById("members-list");
    tbody.innerHTML = allMembers.map((m) => {
        const canEdit = ["admin", "leader"].includes(currentUser.role) || currentUser.id === m.member_id;
        const actions = [];
        const encodedName = encodeInlineValue(m.name);
        const encodedEmail = encodeInlineValue(m.email);

        if (canEdit) {
            actions.push(`<button onclick="openEditMember(${m.member_id}, '${encodedName}', '${encodedEmail}')" class="text-[var(--accent)] hover:underline text-sm">Edit</button>`);
        } else {
            actions.push(`<span class="text-gray-400 text-sm">Locked</span>`);
        }

        if (currentUser.role === "admin" && currentUser.id !== m.member_id) {
            actions.push(`<button onclick="deleteMember(${m.member_id}, '${encodedName}')" class="text-red-600 hover:underline text-sm">Delete</button>`);
        }

        return `
            <tr class="border-b">
                <td class="p-3">${m.student_id}</td>
                <td class="p-3">${m.name}</td>
                <td class="p-3">${m.email}</td>
                <td class="p-3">${m.role}</td>
                <td class="p-3">${m.groups || "-"}</td>
                <td class="p-3 space-x-3">${actions.join("")}</td>
            </tr>
        `;
    }).join("");
}

async function saveNewMember() {
    const student_id = document.getElementById("nm-student-id").value.trim().toLowerCase();
    const name = document.getElementById("nm-name").value.trim();
    const email = document.getElementById("nm-email").value.trim();
    const role = document.getElementById("nm-role").value;
    const password = document.getElementById("nm-pass").value;
    const group_ids = Array.from(document.querySelectorAll(".new-member-group-checkbox:checked"))
        .map((cb) => Number(cb.value));

    const res = await fetch("/api/members", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({student_id, name, email, role, password, group_ids})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("member-modal");
    await initApp();
}

function openEditMember(id, encodedName, encodedEmail) {
    document.getElementById("em-id").value = id;
    document.getElementById("em-name").value = decodeInlineValue(encodedName);
    document.getElementById("em-email").value = decodeInlineValue(encodedEmail);
    document.getElementById("em-pass").value = "";
    document.getElementById("edit-member-modal").classList.remove("hidden");
}

async function saveMember() {
    const id = document.getElementById("em-id").value;
    const name = document.getElementById("em-name").value.trim();
    const email = document.getElementById("em-email").value.trim();
    const password = document.getElementById("em-pass").value;

    const res = await fetch(`/api/members/${id}`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name, email, password})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("edit-member-modal");
    await checkSession();
}

async function deleteMember(id, encodedName) {
    const name = decodeInlineValue(encodedName);
    if (!confirm(`Delete member "${name}"? This will also remove their group and task assignments.`)) {
        return;
    }

    const res = await fetch(`/api/members/${id}`, {method: "DELETE"});
    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    await initApp();
}

function populateOwnerSelects() {
    const options = allMembers.map((m) =>
        `<option value="${m.member_id}">${m.name} (${m.student_id})</option>`
    ).join("");

    document.getElementById("project-owner").innerHTML = `<option value="">No owner</option>${options}`;
    document.getElementById("subproject-owner").innerHTML = `<option value="">No owner</option>${options}`;
}

async function loadGroups() {
    const res = await fetch("/api/groups");
    allGroups = await res.json();
    populateNewMemberGroups();
    document.getElementById("new-group-btn").classList.toggle("hidden", currentUser.role !== "admin");

    const groupList = document.getElementById("group-list");
    groupList.innerHTML = allGroups.map((g) => `
        <div class="bg-white border rounded-2xl p-4">
            <div class="flex justify-between items-start gap-3">
                <div>
                    <div class="font-medium">${g.group_name}</div>
                    <div class="text-sm text-[var(--muted)] mt-1">${g.description || ""}</div>
                </div>
                <div class="flex items-center gap-3">
                    <div class="text-xs px-3 py-1 rounded-full bg-[var(--soft)]">${g.member_count} members</div>
                    ${currentUser.role === "admin"
                        ? `
                            <button onclick="openEditGroup(${g.group_id}, '${encodeInlineValue(g.group_name)}', '${encodeInlineValue(g.description || "")}')" class="text-[var(--accent)] hover:underline text-sm whitespace-nowrap">Edit description</button>
                            <button onclick="openGroupMembersModal(${g.group_id}, '${encodeInlineValue(g.group_name)}')" class="text-[var(--accent)] hover:underline text-sm whitespace-nowrap">Manage members</button>
                        `
                        : ""}
                </div>
            </div>
        </div>
    `).join("");
}

function openEditGroup(id, encodedName, encodedDescription) {
    document.getElementById("eg-id").value = id;
    document.getElementById("eg-name").value = decodeInlineValue(encodedName);
    document.getElementById("eg-desc").value = decodeInlineValue(encodedDescription);
    document.getElementById("edit-group-modal").classList.remove("hidden");
}

async function openGroupMembersModal(id, encodedName) {
    const name = decodeInlineValue(encodedName);
    document.getElementById("gm-id").value = id;
    document.getElementById("gm-name").value = name;

    const memberBox = document.getElementById("gm-members");
    memberBox.innerHTML = '<div class="text-sm text-[var(--muted)]">Loading...</div>';
    document.getElementById("group-members-modal").classList.remove("hidden");

    const res = await fetch(`/api/groups/${id}/members`);
    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        closeModal("group-members-modal");
        return;
    }

    const selectedIds = new Set(data.member_ids || []);
    memberBox.innerHTML = allMembers.map((member) => `
        <label class="flex items-center space-x-2 bg-white border rounded-xl px-3 py-2">
            <input
                type="checkbox"
                class="group-member-checkbox"
                value="${member.member_id}"
                ${selectedIds.has(member.member_id) ? "checked" : ""}
            >
            <span class="text-sm">${member.name} (${member.student_id}, ${member.role})</span>
        </label>
    `).join("");
}

async function saveGroupDescription() {
    const id = document.getElementById("eg-id").value;
    const description = document.getElementById("eg-desc").value.trim();

    const res = await fetch(`/api/groups/${id}`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({description})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("edit-group-modal");
    await loadGroups();
}

async function saveGroupMembers() {
    const id = document.getElementById("gm-id").value;
    const member_ids = Array.from(document.querySelectorAll(".group-member-checkbox:checked"))
        .map((cb) => Number(cb.value));

    const res = await fetch(`/api/groups/${id}/members`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({member_ids})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("group-members-modal");
    await initApp();
}

async function saveGroup() {
    const group_name = document.getElementById("group-name").value.trim();
    const description = document.getElementById("group-desc").value.trim();

    const res = await fetch("/api/groups", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({group_name, description})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("group-modal");
    document.getElementById("group-name").value = "";
    document.getElementById("group-desc").value = "";
    await loadGroups();
}

async function loadProjects() {
    const res = await fetch("/api/projects");
    allProjects = await res.json();

    document.getElementById("project-list").innerHTML = allProjects.map((p) => `
        <div class="bg-white border rounded-2xl p-4">
            <div class="flex justify-between items-start gap-3">
                <div>
                    <div class="font-medium text-lg">${p.title}</div>
                    <div class="text-sm text-[var(--muted)] mt-1">${p.description || ""}</div>
                    <div class="text-xs text-[var(--subtle)] mt-3">
                        Owner: ${p.owner_name || "—"} · Status: ${p.status}
                    </div>
                </div>
                <div class="text-xs px-3 py-1 rounded-full bg-[var(--soft)]">
                    ${p.subproject_count} subprojects
                </div>
            </div>
        </div>
    `).join("");
}

async function saveProject() {
    const title = document.getElementById("project-title").value.trim();
    const description = document.getElementById("project-desc").value.trim();
    const owner_member_id = document.getElementById("project-owner").value || null;

    const res = await fetch("/api/projects", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({title, description, owner_member_id})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("project-modal");
    document.getElementById("project-title").value = "";
    document.getElementById("project-desc").value = "";
    await loadProjects();
    populateProjectSelects();
}

function populateProjectSelects() {
    const options = allProjects.map((p) =>
        `<option value="${p.project_id}">${p.title}</option>`
    ).join("");
    document.getElementById("subproject-project").innerHTML = options;
    document.getElementById("task-project").innerHTML = options;
}

async function loadSubprojects() {
    const res = await fetch("/api/subprojects");
    allSubprojects = await res.json();

    document.getElementById("subproject-list").innerHTML = allSubprojects.map((sp) => `
        <div class="bg-white border rounded-2xl p-4">
            <div class="font-medium">${sp.title}</div>
            <div class="text-sm text-[var(--muted)] mt-1">${sp.description || ""}</div>
            <div class="text-xs text-[var(--subtle)] mt-3">
                Project: ${sp.project_title} · Owner: ${sp.owner_name || "—"} · Status: ${sp.status}
            </div>
        </div>
    `).join("");
}

async function saveSubproject() {
    const project_id = document.getElementById("subproject-project").value;
    const title = document.getElementById("subproject-title").value.trim();
    const description = document.getElementById("subproject-desc").value.trim();
    const owner_member_id = document.getElementById("subproject-owner").value || null;

    const res = await fetch("/api/subprojects", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({project_id, title, description, owner_member_id})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("subproject-modal");
    document.getElementById("subproject-title").value = "";
    document.getElementById("subproject-desc").value = "";
    await loadSubprojects();
    populateSubprojectOptions();
}

function populateSubprojectOptions() {
    const projectId = Number(document.getElementById("task-project").value);
    const filtered = allSubprojects.filter((sp) => sp.project_id == projectId);
    document.getElementById("task-subproject").innerHTML = filtered.map((sp) =>
        `<option value="${sp.subproject_id}">${sp.title}</option>`
    ).join("");
}

async function loadTasks() {
    const r = await fetch("/api/tasks");
    allTasks = await r.json();
    const tasks = allTasks;

    const timelineTasks = [...tasks].sort((a, b) => {
        if (!a.deadline && !b.deadline) return 0;
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return new Date(a.deadline) - new Date(b.deadline);
    });

    document.getElementById("timetable-list").innerHTML = timelineTasks.map((t) => {
        const dateStr = t.deadline
            ? `${new Date(t.deadline).toLocaleDateString()} ${new Date(t.deadline).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}`
            : "No deadline";

        return `
            <div class="timeline-item">
                <div class="text-sm font-bold">${dateStr}</div>
                <div class="bg-white border p-4 rounded-2xl mt-1">
                    <div class="flex items-start justify-between gap-3">
                        <div class="font-semibold text-[var(--accent)]">${t.title}</div>
                        ${currentUser.role === "admin"
                            ? `<button onclick="openEditTask(${t.task_id})" class="text-[var(--accent)] hover:underline text-sm whitespace-nowrap">Edit</button>`
                            : ""}
                    </div>
                    ${t.description ? `<div class="text-sm text-[var(--muted)] mt-2">${t.description}</div>` : ""}
                    <div class="text-xs text-[var(--muted)] mt-2">
                        ${t.project_title} / ${t.subproject_title}
                    </div>
                    <div class="text-xs text-[var(--subtle)] mt-1">
                        Assignees: ${t.assignee_names || "Unassigned"}
                    </div>
                </div>
            </div>
        `;
    }).join("");

    document.getElementById("project-task-list").innerHTML = timelineTasks.map((task) => `
        <div class="bg-white border rounded-2xl p-4">
            <div class="flex items-start justify-between gap-3">
                <div>
                    <div class="font-medium">${task.title}</div>
                    ${task.description ? `<div class="text-sm text-[var(--muted)] mt-1">${task.description}</div>` : ""}
                    <div class="text-xs text-[var(--subtle)] mt-3">${task.project_title} / ${task.subproject_title}</div>
                    <div class="text-xs text-[var(--subtle)] mt-1">Urgency: ${Number(task.urgency_score).toFixed(2)}</div>
                </div>
                ${currentUser.role === "admin"
                    ? `<button onclick="openEditTask(${task.task_id})" class="text-[var(--accent)] hover:underline text-sm whitespace-nowrap">Edit</button>`
                    : ""}
            </div>
        </div>
    `).join("");
}

function openEditTask(taskId) {
    const task = allTasks.find((item) => item.task_id === taskId);
    if (!task) {
        alert("Task not found");
        return;
    }

    const urgency = Number(task.urgency_score ?? 0.5).toFixed(2);
    document.getElementById("et-id").value = task.task_id;
    document.getElementById("et-title").value = task.title || "";
    document.getElementById("et-desc").value = task.description || "";
    document.getElementById("et-importance").value = urgency;
    updateTaskUrgencyLabel(urgency);
    document.getElementById("edit-task-modal").classList.remove("hidden");
}

async function saveTaskEdit() {
    const task_id = document.getElementById("et-id").value;
    const title = document.getElementById("et-title").value.trim();
    const description = document.getElementById("et-desc").value.trim();
    const urgency = document.getElementById("et-importance").value;

    const res = await fetch(`/api/tasks/${task_id}`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({title, description, urgency})
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("edit-task-modal");
    await loadTasks();
}

async function svTask() {
    const assigned_member_ids = Array.from(document.querySelectorAll(".assign-member-checkbox:checked"))
        .map((el) => Number(el.value));

    const payload = {
        subproject_id: document.getElementById("task-subproject").value,
        title: document.getElementById("tt").value.trim(),
        deadline: document.getElementById("td").value,
        importance: document.getElementById("ti").value,
        assigned_member_ids,
        description: ""
    };

    const res = await fetch("/api/tasks", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
        alert(data.error || "Failed");
        return;
    }

    closeModal("task-modal");
    document.getElementById("tt").value = "";
    document.getElementById("td").value = "";
    document.getElementById("ti").value = "0.50";
    updateNewTaskUrgencyLabel("0.50");
    document.querySelectorAll(".assign-member-checkbox").forEach((cb) => {
        cb.checked = false;
    });
    await loadTasks();
}

updateNewTaskUrgencyLabel(document.getElementById("ti").value);
checkSession();
