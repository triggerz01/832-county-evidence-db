"""832 工程调研任务与县域产业证据管理系统 —— Flask 后端（选项 1：传统动态网站）。

运行：
    python app.py
    http://127.0.0.1:5000

设计要点：
  * 所有查询、统计、写入都在服务端执行，模板只渲染结果；
  * 权限按角色在 SQL 层收窄（不是前端隐藏按钮）；
  * 提交版本、审核、发布三类写操作各自包一个事务，并写审计日志。
"""

import functools
import os
from datetime import datetime

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

import db as database

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "832-research-demo-secret-2026")
database.init_app(app)

ROLE_NAMES = {
    "admin": "系统管理员",
    "leader": "调研队长",
    "member": "调研队员",
    "reviewer": "成果审核员",
    "researcher": "研究员",
}
STATE_NAMES = {
    "已分配": "已分配", "进行中": "进行中", "待审核": "待审核",
    "退回补正": "退回补正", "已完成": "已完成", "已发布": "已发布",
}
CASE_STATES = ["草稿", "待审核", "退回补正", "已审核", "已发布"]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@app.before_request
def load_user():
    g.user = None
    uid = session.get("user_id")
    if uid is not None:
        g.user = database.query_one(
            "SELECT * FROM user_account WHERE user_id = ?", (uid,)
        )
        if g.user is None:
            session.clear()


@app.context_processor
def inject_globals():
    return {
        "current_user": g.get("user"),
        "role_names": ROLE_NAMES,
        "state_names": STATE_NAMES,
        "today": today(),
    }


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @functools.wraps(view)
        def wrapped(**kwargs):
            if g.user is None:
                return redirect(url_for("login", next=request.path))
            if g.user["role"] not in roles:
                abort(403)
            return view(**kwargs)

        return wrapped

    return decorator


def case_scope():
    """案例可见范围：返回 (SQL 条件, 参数)。权限在 SQL 层收窄。"""
    user = g.get("user")
    if user is None:
        return "ic.status = '已发布'", ()
    if user["role"] in ("admin", "leader", "reviewer", "researcher"):
        return "1 = 1", ()
    return "(ic.status = '已发布' OR ic.owner_id = ?)", (user["user_id"],)


def task_scope():
    user = g.get("user")
    if user is None:
        return "1 = 0", ()
    if user["role"] in ("admin", "leader", "reviewer", "researcher"):
        return "1 = 1", ()
    return ("t.task_id IN (SELECT task_id FROM task_assignment WHERE user_id = ?)",
            (user["user_id"],))


def get_case_or_404(case_id):
    cond, args = case_scope()
    row = database.query_one(
        f"""SELECT ic.*, c.county_name_raw, c.province_raw, u.display_name AS owner_name
              FROM industry_case ic
              JOIN county c ON c.county_id = ic.county_id
              LEFT JOIN user_account u ON u.user_id = ic.owner_id
             WHERE ic.case_id = ? AND {cond}""",
        (case_id, *args),
    )
    if row is None:
        abort(404)
    return row


def get_task_or_404(task_id):
    cond, args = task_scope()
    row = database.query_one(
        f"""SELECT v.*, u.display_name AS created_by_name
              FROM v_task_progress v
              JOIN field_task ft ON ft.task_id = v.task_id
              JOIN user_account u ON u.user_id = ft.created_by
             WHERE v.task_id = ? AND {cond.replace('t.', 'v.')}""",
        (task_id, *args),
    )
    if row is None:
        abort(404)
    return row


# ---------------------------------------------------------------- 登录与首页

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = (request.form.get("display_name") or "").strip()
        pwd = request.form.get("password") or ""
        user = database.query_one(
            "SELECT * FROM user_account WHERE display_name = ?", (name,)
        )
        if user is None or not check_password_hash(user["password_hash"] or "", pwd):
            flash("账号或口令不正确", "error")
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            return redirect(request.args.get("next") or url_for("dashboard"))
    accounts = database.query(
        "SELECT display_name, role FROM user_account ORDER BY user_id"
    )
    return render_template("login.html", accounts=accounts)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def dashboard():
    cond, args = case_scope()
    visible_cases = database.scalar(
        f"SELECT COUNT(*) FROM industry_case ic WHERE {cond}", args
    )
    published_cases = database.scalar(
        "SELECT COUNT(*) FROM industry_case WHERE status = '已发布'"
    )
    tcond, targs = task_scope()
    visible_tasks = database.scalar(
        f"SELECT COUNT(*) FROM v_task_progress v WHERE {tcond.replace('t.', 'v.')}",
        targs,
    )
    stats = {
        "reports": database.scalar("SELECT COUNT(*) FROM public_report"),
        "counties": database.scalar("SELECT COUNT(*) FROM county"),
        "documents": database.scalar("SELECT COUNT(*) FROM source_document"),
        "cases": visible_cases,
        "published_cases": published_cases,
        "tasks": visible_tasks,
        "projects": database.scalar("SELECT COUNT(*) FROM government_project"),
        "locations": database.scalar("SELECT COUNT(*) FROM project_location"),
        "funding": database.scalar(
            "SELECT ROUND(SUM(budget_wan), 2) FROM project_snapshot"
            " WHERE snapshot_kind = '年度计划'"
        ),
    }
    overdue = database.query(
        """SELECT v.task_id, v.county_name_raw, v.lead_name, v.required_kind, v.due_at
             FROM v_task_progress v
            WHERE v.due_at < ?
              AND NOT EXISTS (
                    SELECT 1 FROM deliverable_version d
                     WHERE d.task_id = v.task_id
                       AND d.kind = v.required_kind
                       AND substr(d.submitted_at, 1, 10) <= v.due_at)""",
        (today(),),
    )
    states = database.query(
        "SELECT state, COUNT(*) AS n FROM field_task GROUP BY state ORDER BY n DESC"
    )
    my_tasks = []
    if g.user is not None:
        my_tasks = database.query(
            """SELECT v.task_id, v.topic, v.county_name_raw, v.state, v.due_at
                 FROM v_task_progress v
                 JOIN task_assignment a ON a.task_id = v.task_id
                WHERE a.user_id = ?
                ORDER BY v.due_at""",
            (g.user["user_id"],),
        )
    return render_template(
        "dashboard.html", stats=stats, overdue=overdue, states=states,
        my_tasks=my_tasks,
    )


# ---------------------------------------------------------------- 资料检索

@app.route("/reports")
def reports():
    kw = (request.args.get("kw") or "").strip()
    province = (request.args.get("province") or "").strip()
    where, args = ["1 = 1"], []
    if kw:
        where.append("(d.title LIKE ? OR c.county_name_raw LIKE ?)")
        args += [f"%{kw}%", f"%{kw}%"]
    if province:
        where.append("c.province_raw = ?")
        args.append(province)
    rows = database.query(
        f"""SELECT r.report_id, d.title, r.published_date,
                   c.province_raw, c.county_name_raw, d.url,
                   (SELECT COUNT(DISTINCT ce.case_id)
                      FROM source_excerpt se
                      JOIN case_evidence ce ON ce.excerpt_id = se.excerpt_id
                     WHERE se.document_id = d.document_id) AS case_count
              FROM public_report r
              JOIN county c ON c.county_id = r.county_id
              JOIN source_document d ON d.document_id = r.document_id
             WHERE {' AND '.join(where)}
             ORDER BY r.published_date DESC
             LIMIT 200""",
        args,
    )
    provinces = database.query(
        "SELECT province_raw, COUNT(*) AS n FROM county GROUP BY province_raw ORDER BY n DESC"
    )
    total = database.scalar("SELECT COUNT(*) FROM public_report")
    no_case = database.scalar(
        """SELECT COUNT(*) FROM public_report pr
            WHERE NOT EXISTS (
                  SELECT 1 FROM source_excerpt se
                  JOIN case_evidence ce ON ce.excerpt_id = se.excerpt_id
                 WHERE se.document_id = pr.document_id)"""
    )
    return render_template(
        "reports.html", rows=rows, provinces=provinces, kw=kw,
        province=province, total=total, no_case=no_case,
    )


# ---------------------------------------------------------------- 案例管理

@app.route("/cases")
def cases():
    cond, args = case_scope()
    where, wargs = [cond], list(args)
    county = (request.args.get("county") or "").strip()
    industry = (request.args.get("industry") or "").strip()
    mech = (request.args.get("mechanism") or "").strip()
    status = (request.args.get("status") or "").strip()
    if county:
        where.append("c.county_name_raw LIKE ?")
        wargs.append(f"%{county}%")
    if industry:
        where.append("ic.industry LIKE ?")
        wargs.append(f"%{industry}%")
    if status:
        where.append("ic.status = ?")
        wargs.append(status)
    if mech:
        where.append(
            """EXISTS (SELECT 1 FROM case_mechanism cm JOIN mechanism m
                        ON m.mechanism_id = cm.mechanism_id
                       WHERE cm.case_id = ic.case_id AND m.name = ?)"""
        )
        wargs.append(mech)
    rows = database.query(
        f"""SELECT ic.case_id, ic.title, ic.industry, ic.status, ic.data_kind,
                   c.province_raw, c.county_name_raw,
                   u.display_name AS owner_name,
                   (SELECT group_concat(m.name, '、')
                      FROM case_mechanism cm JOIN mechanism m
                        ON m.mechanism_id = cm.mechanism_id
                     WHERE cm.case_id = ic.case_id) AS mechanisms
              FROM industry_case ic
              JOIN county c ON c.county_id = ic.county_id
              LEFT JOIN user_account u ON u.user_id = ic.owner_id
             WHERE {' AND '.join(where)}
             ORDER BY ic.case_id""",
        wargs,
    )
    mechanisms = database.query("SELECT name FROM mechanism ORDER BY mechanism_id")
    return render_template(
        "cases.html", rows=rows, mechanisms=mechanisms, county=county,
        industry=industry, mech=mech, status=status, states=CASE_STATES,
    )


@app.route("/cases/new", methods=["GET", "POST"])
@login_required
def case_new():
    if g.user["role"] not in ("admin", "leader", "member", "reviewer"):
        abort(403)
    if request.method == "POST":
        return _save_case(None)
    return render_template(
        "case_form.html", case=None, counties=_counties(),
        mechanisms=_mechanisms(), excerpts=_excerpts(), tasks=_tasks_for_form(),
        selected_mech=[], selected_excerpts=[],
    )


def _counties():
    return database.query(
        "SELECT county_id, province_raw, county_name_raw FROM county ORDER BY county_id"
    )


def _mechanisms():
    return database.query("SELECT mechanism_id, name FROM mechanism ORDER BY mechanism_id")


def _excerpts():
    return database.query(
        """SELECT se.excerpt_id, se.locator, se.summary, d.title
             FROM source_excerpt se
             JOIN source_document d ON d.document_id = se.document_id
            ORDER BY se.excerpt_id"""
    )


def _tasks_for_form():
    return database.query(
        "SELECT task_id, topic FROM field_task ORDER BY task_id"
    )


def _save_case(case_id):
    form = request.form
    county_id = form.get("county_id") or ""
    title = (form.get("title") or "").strip()
    industry = (form.get("industry") or "").strip()
    claim = (form.get("claim_summary") or "").strip()
    task_id = form.get("task_id") or None
    data_kind = form.get("data_kind") or "课程模拟"
    if data_kind not in ("公开报道整理", "课程模拟"):
        data_kind = "课程模拟"
    mech_ids = [int(x) for x in form.getlist("mechanism_id") if x]
    excerpt_ids = [int(x) for x in form.getlist("excerpt_id") if x]

    if not (county_id and title and industry and claim):
        flash("县域、标题、产业、说法摘要都必须填写", "error")
        return redirect(request.url)

    with database.transaction() as conn:
        if case_id is None:
            new_id = database.scalar("SELECT COUNT(*) FROM industry_case") + 1
            case_id = f"C-{new_id:03d}"
            while database.scalar(
                "SELECT 1 FROM industry_case WHERE case_id = ?", (case_id,)
            ):
                new_id += 1
                case_id = f"C-{new_id:03d}"
            conn.execute(
                """INSERT INTO industry_case
                   (case_id, county_id, task_id, title, industry, claim_summary,
                    status, data_kind, owner_id)
                   VALUES (?,?,?,?,?,?,'草稿',?,?)""",
                (case_id, county_id, task_id, title, industry, claim,
                 data_kind, g.user["user_id"]),
            )
            action = f"新建案例草稿 {case_id}"
        else:
            conn.execute(
                """UPDATE industry_case
                      SET county_id = ?, task_id = ?, title = ?, industry = ?,
                          claim_summary = ?, data_kind = ?
                    WHERE case_id = ?""",
                (county_id, task_id, title, industry, claim, data_kind, case_id),
            )
            conn.execute("DELETE FROM case_mechanism WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM case_evidence WHERE case_id = ?", (case_id,))
            action = f"修改案例草稿 {case_id}"
        for mid in mech_ids:
            conn.execute(
                "INSERT INTO case_mechanism(case_id, mechanism_id) VALUES (?,?)",
                (case_id, mid),
            )
        for eid in excerpt_ids:
            conn.execute(
                "INSERT INTO case_evidence(case_id, excerpt_id) VALUES (?,?)",
                (case_id, eid),
            )
        database.write_log(conn, g.user["user_id"], task_id, action, now_text(),
                           case_id=case_id)
    flash(f"案例 {case_id} 已保存为草稿", "ok")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<case_id>")
def case_detail(case_id):
    case = get_case_or_404(case_id)
    mechanisms = database.query(
        """SELECT m.name FROM case_mechanism cm JOIN mechanism m
             ON m.mechanism_id = cm.mechanism_id
            WHERE cm.case_id = ? ORDER BY m.mechanism_id""",
        (case_id,),
    )
    excerpts = database.query(
        """SELECT se.excerpt_id, se.locator, se.summary, d.title, d.url
             FROM case_evidence ce
             JOIN source_excerpt se ON se.excerpt_id = ce.excerpt_id
             JOIN source_document d ON d.document_id = se.document_id
            WHERE ce.case_id = ?
            ORDER BY se.excerpt_id""",
        (case_id,),
    )
    history = database.query(
        """SELECT a.action, a.acted_at, u.display_name
             FROM audit_log a JOIN user_account u ON u.user_id = a.actor_id
            WHERE a.case_id = ? ORDER BY a.log_id DESC""",
        (case_id,),
    )
    can_edit = (
        g.user is not None
        and case["status"] in ("草稿", "退回补正")
        and (case["owner_id"] == g.user["user_id"] or g.user["role"] == "admin")
    )
    return render_template(
        "case_detail.html", case=case, mechanisms=mechanisms, excerpts=excerpts,
        history=history, can_edit=can_edit,
    )


@app.route("/cases/<case_id>/edit", methods=["GET", "POST"])
@login_required
def case_edit(case_id):
    case = get_case_or_404(case_id)
    if case["status"] not in ("草稿", "退回补正"):
        abort(403)
    if case["owner_id"] != g.user["user_id"] and g.user["role"] != "admin":
        abort(403)
    if request.method == "POST":
        return _save_case(case_id)
    selected_mech = [r["mechanism_id"] for r in database.query(
        "SELECT mechanism_id FROM case_mechanism WHERE case_id = ?", (case_id,))]
    selected_excerpts = [r["excerpt_id"] for r in database.query(
        "SELECT excerpt_id FROM case_evidence WHERE case_id = ?", (case_id,))]
    return render_template(
        "case_form.html", case=case, counties=_counties(),
        mechanisms=_mechanisms(), excerpts=_excerpts(), tasks=_tasks_for_form(),
        selected_mech=selected_mech, selected_excerpts=selected_excerpts,
    )


@app.route("/cases/<case_id>/delete", methods=["POST"])
@login_required
def case_delete(case_id):
    case = get_case_or_404(case_id)
    if case["status"] != "草稿":
        abort(403)
    if case["owner_id"] != g.user["user_id"] and g.user["role"] != "admin":
        abort(403)
    with database.transaction() as conn:
        conn.execute("DELETE FROM case_mechanism WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM case_evidence WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM industry_case WHERE case_id = ?", (case_id,))
        database.write_log(conn, g.user["user_id"], case["task_id"],
                           f"删除案例草稿 {case_id}", now_text(), case_id=case_id)
    flash(f"案例 {case_id} 已删除（仅草稿可删）", "ok")
    return redirect(url_for("cases"))


@app.route("/cases/<case_id>/submit", methods=["POST"])
@login_required
def case_submit(case_id):
    case = get_case_or_404(case_id)
    if case["owner_id"] != g.user["user_id"]:
        abort(403)
    if case["status"] not in ("草稿", "退回补正"):
        abort(403)
    has_evidence = database.scalar(
        "SELECT 1 FROM case_evidence WHERE case_id = ? LIMIT 1", (case_id,)
    )
    if not has_evidence:
        flash("这条案例还没挂任何出处摘录，不能提交审核——没有出处的说法进不了对外口径", "error")
        return redirect(url_for("case_detail", case_id=case_id))
    with database.transaction() as conn:
        conn.execute(
            "UPDATE industry_case SET status = '待审核' WHERE case_id = ?", (case_id,)
        )
        database.write_log(conn, g.user["user_id"], case["task_id"],
                           f"提交案例待审 {case_id}", now_text(), case_id=case_id)
    flash("已提交审核", "ok")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<case_id>/review", methods=["POST"])
@roles_required("reviewer", "admin")
def case_review(case_id):
    case = get_case_or_404(case_id)
    if case["status"] != "待审核":
        abort(403)
    if case["owner_id"] == g.user["user_id"]:
        abort(403)
    decision = request.form.get("decision")
    reason = (request.form.get("reason") or "").strip()
    if decision not in ("通过", "退回"):
        abort(400)
    if decision == "退回" and not reason:
        flash("退回必须写明理由", "error")
        return redirect(url_for("case_detail", case_id=case_id))
    target = "已审核" if decision == "通过" else "退回补正"
    with database.transaction() as conn:
        conn.execute(
            "UPDATE industry_case SET status = ? WHERE case_id = ?", (target, case_id)
        )
        database.write_log(
            conn, g.user["user_id"], case["task_id"],
            f"案例审核{decision} {case_id}：{reason or '来源与口径已核对'}",
            now_text(), case_id=case_id,
        )
    flash(f"已{decision}", "ok")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<case_id>/publish", methods=["POST"])
@roles_required("leader", "admin")
def case_publish(case_id):
    case = get_case_or_404(case_id)
    if case["status"] != "已审核":
        abort(403)
    with database.transaction() as conn:
        conn.execute(
            "UPDATE industry_case SET status = '已发布' WHERE case_id = ?", (case_id,)
        )
        database.write_log(conn, g.user["user_id"], case["task_id"],
                           f"发布案例 {case_id}", now_text(), case_id=case_id)
    flash("已发布，公众可见", "ok")
    return redirect(url_for("case_detail", case_id=case_id))


# ---------------------------------------------------------------- 任务协作

@app.route("/tasks")
def tasks():
    cond, args = task_scope()
    where, wargs = [cond.replace("t.", "v.")], list(args)
    state = (request.args.get("state") or "").strip()
    kw = (request.args.get("kw") or "").strip()
    if state:
        where.append("v.state = ?")
        wargs.append(state)
    if kw:
        where.append("(v.county_name_raw LIKE ? OR v.topic LIKE ?)")
        wargs += [f"%{kw}%", f"%{kw}%"]
    rows = database.query(
        f"""SELECT v.*, (v.due_at < ? AND v.state NOT IN ('已完成','已发布')) AS overdue
              FROM v_task_progress v
             WHERE {' AND '.join(where)}
             ORDER BY v.due_at""",
        [today(), *wargs],
    )
    return render_template("tasks.html", rows=rows, state=state, kw=kw,
                           states=list(STATE_NAMES))


@app.route("/tasks/new", methods=["GET", "POST"])
@roles_required("leader", "admin")
def task_new():
    if request.method == "POST":
        form = request.form
        county_id = form.get("county_id") or ""
        topic = (form.get("topic") or "").strip()
        kind = form.get("required_kind") or ""
        due = form.get("due_at") or ""
        assignee = form.get("assignee") or ""
        if not (county_id and topic and kind and due and assignee):
            flash("县域、主题、材料类型、截止日、负责人均为必填", "error")
            return redirect(request.url)
        task_id = "T-" + str(database.scalar("SELECT COUNT(*) FROM field_task") + 1).zfill(3)
        while database.scalar("SELECT 1 FROM field_task WHERE task_id = ?", (task_id,)):
            task_id = "T-" + str(int(task_id[2:]) + 1).zfill(3)
        with database.transaction() as conn:
            conn.execute(
                """INSERT INTO field_task
                   (task_id, county_id, topic, required_kind, due_at, state,
                    created_by, data_kind)
                   VALUES (?,?,?,?,?,'已分配',?,'课程模拟')""",
                (task_id, county_id, topic, kind, due, g.user["user_id"]),
            )
            conn.execute(
                "INSERT INTO task_assignment(task_id, user_id, is_lead) VALUES (?,?,1)",
                (task_id, assignee),
            )
            database.write_log(conn, g.user["user_id"], task_id,
                               f"创建并指派 {task_id}", now_text())
        flash(f"任务 {task_id} 已指派", "ok")
        return redirect(url_for("task_detail", task_id=task_id))
    return render_template(
        "task_form.html", counties=_counties(),
        members=database.query(
            "SELECT user_id, display_name FROM user_account WHERE role IN ('member','leader')"
        ),
        kinds=["调研日志", "新闻速递", "案例报告", "资料包"],
    )


@app.route("/tasks/<task_id>")
def task_detail(task_id):
    task = get_task_or_404(task_id)
    assignments = database.query(
        """SELECT u.display_name, a.is_lead FROM task_assignment a
             JOIN user_account u ON u.user_id = a.user_id
            WHERE a.task_id = ? ORDER BY a.is_lead DESC""",
        (task_id,),
    )
    versions = database.query(
        """SELECT v.*, u.display_name AS submitter
             FROM deliverable_version v
             JOIN user_account u ON u.user_id = v.submitted_by
            WHERE v.task_id = ? ORDER BY v.version_no DESC""",
        (task_id,),
    )
    reviews = database.query(
        """SELECT r.*, u.display_name AS reviewer, v.version_no
             FROM review_action r
             JOIN user_account u ON u.user_id = r.reviewer_id
             JOIN deliverable_version v ON v.version_id = r.version_id
            WHERE v.task_id = ? ORDER BY r.review_id DESC""",
        (task_id,),
    )
    logs = database.query(
        """SELECT a.action, a.acted_at, u.display_name
             FROM audit_log a JOIN user_account u ON u.user_id = a.actor_id
            WHERE a.task_id = ? ORDER BY a.log_id DESC""",
        (task_id,),
    )
    latest = versions[0] if versions else None
    can_submit = (
        g.user is not None
        and task["state"] in ("已分配", "进行中", "退回补正")
        and database.scalar(
            "SELECT 1 FROM task_assignment WHERE task_id = ? AND user_id = ?",
            (task_id, g.user["user_id"]),
        )
    )
    can_review = (
        g.user is not None
        and task["state"] == "待审核"
        and g.user["role"] in ("reviewer", "admin")
        and latest is not None
        and latest["submitted_by"] != g.user["user_id"]
    )
    can_publish = (
        g.user is not None and g.user["role"] in ("leader", "admin")
        and task["state"] == "已完成"
    )
    return render_template(
        "task_detail.html", task=task, assignments=assignments, versions=versions,
        reviews=reviews, logs=logs, latest=latest, can_submit=can_submit,
        can_review=can_review, can_publish=can_publish,
        cases=database.query("SELECT case_id, title FROM industry_case ORDER BY case_id"),
    )


@app.route("/tasks/<task_id>/submit", methods=["POST"])
@login_required
def task_submit(task_id):
    task = get_task_or_404(task_id)
    if task["state"] not in ("已分配", "进行中", "退回补正"):
        abort(403)
    if not database.scalar(
        "SELECT 1 FROM task_assignment WHERE task_id = ? AND user_id = ?",
        (task_id, g.user["user_id"]),
    ):
        abort(403)
    title = (request.form.get("title") or "").strip()
    note = (request.form.get("note") or "").strip()
    case_id = request.form.get("case_id") or None
    if not title or not note:
        flash("材料标题和说明都必须填写", "error")
        return redirect(url_for("task_detail", task_id=task_id))

    version_no = (database.scalar(
        "SELECT MAX(version_no) FROM deliverable_version WHERE task_id = ?", (task_id,)
    ) or 0) + 1

    with database.transaction() as conn:
        doc_id = conn.execute(
            """INSERT INTO source_document
               (external_id, url, publisher, title, source_kind, checked_on)
               VALUES (NULL, ?, ?, ?, '提交材料', ?)""",
            (f"urn:deliverable:{task_id}:{version_no}", g.user["display_name"],
             title, today()),
        ).lastrowid
        conn.execute(
            """INSERT INTO deliverable_version
               (task_id, version_no, kind, title, document_id, case_id, note,
                submitted_by, submitted_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (task_id, version_no, task["required_kind"], title, doc_id, case_id,
             note, g.user["user_id"], now_text()),
        )
        conn.execute(
            "UPDATE field_task SET state = '待审核' WHERE task_id = ?", (task_id,)
        )
        database.write_log(conn, g.user["user_id"], task_id,
                           f"提交第 {version_no} 版 {task['required_kind']}", now_text())
    flash(f"已提交第 {version_no} 版，等待审核", "ok")
    return redirect(url_for("task_detail", task_id=task_id))


@app.route("/tasks/<task_id>/review", methods=["POST"])
@roles_required("reviewer", "admin")
def task_review(task_id):
    task = get_task_or_404(task_id)
    if task["state"] != "待审核":
        abort(403)
    latest = database.query_one(
        "SELECT * FROM deliverable_version WHERE task_id = ? ORDER BY version_no DESC LIMIT 1",
        (task_id,),
    )
    if latest is None:
        abort(400)
    if latest["submitted_by"] == g.user["user_id"]:
        flash("不能审核自己提交的版本", "error")
        return redirect(url_for("task_detail", task_id=task_id))
    decision = request.form.get("decision")
    reason = (request.form.get("reason") or "").strip()
    if decision not in ("通过", "退回"):
        abort(400)
    if decision == "退回" and not reason:
        flash("退回必须写明理由（数据库 CHECK 约束同样要求）", "error")
        return redirect(url_for("task_detail", task_id=task_id))
    target = "已完成" if decision == "通过" else "退回补正"
    with database.transaction() as conn:
        conn.execute(
            """INSERT INTO review_action(version_id, reviewer_id, decision, reason, acted_at)
               VALUES (?,?,?,?,?)""",
            (latest["version_id"], g.user["user_id"], decision,
             reason or "来源与计划口径已核对", now_text()),
        )
        conn.execute(
            "UPDATE field_task SET state = ? WHERE task_id = ?", (target, task_id)
        )
        database.write_log(conn, g.user["user_id"], task_id,
                           f"审核第 {latest['version_no']} 版：{decision}", now_text())
    flash(f"第 {latest['version_no']} 版已{decision}", "ok")
    return redirect(url_for("task_detail", task_id=task_id))


@app.route("/tasks/<task_id>/publish", methods=["POST"])
@roles_required("leader", "admin")
def task_publish(task_id):
    task = get_task_or_404(task_id)
    if task["state"] != "已完成":
        abort(403)
    latest = database.query_one(
        "SELECT * FROM deliverable_version WHERE task_id = ? ORDER BY version_no DESC LIMIT 1",
        (task_id,),
    )
    with database.transaction() as conn:
        conn.execute("UPDATE field_task SET state = '已发布' WHERE task_id = ?", (task_id,))
        if latest and latest["case_id"]:
            conn.execute(
                "UPDATE industry_case SET status = '已发布' WHERE case_id = ?",
                (latest["case_id"],),
            )
        database.write_log(conn, g.user["user_id"], task_id, "发布成果", now_text())
    flash("成果已发布", "ok")
    return redirect(url_for("task_detail", task_id=task_id))


# ---------------------------------------------------------------- 统计与 SQL

@app.route("/stats")
def stats():
    province_rows = database.query(
        """SELECT c.province_raw, COUNT(*) AS report_count
             FROM public_report r JOIN county c ON c.county_id = r.county_id
            GROUP BY c.province_raw ORDER BY report_count DESC LIMIT 8"""
    )
    dual_rows = database.query(
        """SELECT ic.case_id, ic.title, c.county_name_raw
             FROM industry_case ic
             JOIN county c ON c.county_id = ic.county_id
             JOIN case_mechanism cm ON cm.case_id = ic.case_id
             JOIN mechanism m ON m.mechanism_id = cm.mechanism_id
            WHERE ic.status = '已发布' AND m.name IN ('就业','土地流转')
            GROUP BY ic.case_id, ic.title, c.county_name_raw
           HAVING COUNT(DISTINCT m.name) = 2"""
    )
    category_rows = database.query(
        "SELECT * FROM v_project_category ORDER BY planned_funding_wan DESC"
    )
    total_funding = database.scalar(
        "SELECT ROUND(SUM(planned_funding_wan), 6) FROM v_project_category"
    )
    mismatch_rows = database.query(
        """SELECT gp.project_id, gp.project_name, ps.budget_wan,
                  ROUND(SUM(pl.planned_2024_funding_wan), 6) AS row_sum_wan
             FROM government_project gp
             JOIN project_snapshot ps ON ps.project_id = gp.project_id
             JOIN project_location pl ON pl.project_id = gp.project_id
            GROUP BY gp.project_id, gp.project_name, ps.budget_wan
           HAVING ABS(SUM(pl.planned_2024_funding_wan) - ps.budget_wan) > 0.000001"""
    )
    no_case = database.scalar(
        """SELECT COUNT(*) FROM public_report pr
            WHERE NOT EXISTS (
                  SELECT 1 FROM source_excerpt se
                  JOIN case_evidence ce ON ce.excerpt_id = se.excerpt_id
                 WHERE se.document_id = pr.document_id)"""
    )
    overdue_rows = []
    if g.user is not None and g.user["role"] in ("admin", "leader", "reviewer", "researcher"):
        overdue_rows = database.query(
            """SELECT v.task_id, v.county_name_raw, v.lead_name, v.required_kind, v.due_at
                 FROM v_task_progress v
                WHERE v.due_at < ?
                  AND NOT EXISTS (
                        SELECT 1 FROM deliverable_version d
                         WHERE d.task_id = v.task_id
                           AND d.kind = v.required_kind
                           AND substr(d.submitted_at, 1, 10) <= v.due_at)""",
            (today(),),
        )
    issues = database.query(
        "SELECT issue_id, project_name_raw, database_use, do_not_infer, review_status"
        " FROM evidence_issue ORDER BY issue_id"
    )
    return render_template(
        "stats.html", province_rows=province_rows, dual_rows=dual_rows,
        category_rows=category_rows, total_funding=total_funding,
        mismatch_rows=mismatch_rows, no_case=no_case, overdue_rows=overdue_rows,
        issues=issues,
    )


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, message="当前角色没有这项操作权限"), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="记录不存在，或不在你的可见范围内"), 404


if __name__ == "__main__":
    debug = os.environ.get("APP_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, use_reloader=debug, port=port)
