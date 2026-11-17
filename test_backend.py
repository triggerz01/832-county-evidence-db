"""后端端到端测试：在数据库副本上验证权限、事务、状态流转与约束。

运行：
    python test_backend.py

不修改 832_research_sample.sqlite，全部操作在 tmp/test_copy.sqlite 上进行。
"""

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import app as application  # noqa: E402
import db as database  # noqa: E402

TMP = ROOT / "tmp"
TMP.mkdir(exist_ok=True)
TEST_DB = TMP / "test_copy.sqlite"
shutil.copyfile(ROOT / "832_research_sample.sqlite", TEST_DB)
database.DB_PATH = TEST_DB

results = []


def check(name, condition, detail=""):
    results.append((bool(condition), name, detail))
    print(("  PASS " if condition else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))


def login(client, name, pwd="832demo"):
    return client.post("/login", data={"display_name": name, "password": pwd},
                       follow_redirects=True)


def db_row(sql, args=()):
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchone()
    finally:
        conn.close()


def db_exec(sql, args=()):
    conn = sqlite3.connect(TEST_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute(sql, args)
        conn.commit()
    finally:
        conn.close()


def main():
    application.app.config.update(TESTING=True)

    print("\n[1] 登录与角色")
    c_member = application.app.test_client()
    r = login(c_member, "队员甲")
    check("队员甲登录成功", "退出" in r.get_data(as_text=True))
    c_bad = application.app.test_client()
    r = login(c_bad, "队员甲", "wrong")
    check("错误口令被拒绝", "账号或口令不正确" in r.get_data(as_text=True))

    c_reviewer = application.app.test_client()
    login(c_reviewer, "审核员")
    c_leader = application.app.test_client()
    login(c_leader, "队长")
    c_member_b = application.app.test_client()
    login(c_member_b, "队员乙")
    c_public = application.app.test_client()

    print("\n[2] 案例：新建草稿 → 修改 → 提交 → 退回")
    before = db_row("SELECT COUNT(*) AS n FROM industry_case")["n"]
    r = c_member.post("/cases/new", data={
        "county_id": "290", "title": "测试：城西湖莲藕加工与就业", "industry": "莲藕",
        "claim_summary": "测试用说法摘要，仅引用公开报道原文。",
        "data_kind": "公开报道整理", "task_id": "T-002",
        "mechanism_id": ["7", "8"], "excerpt_id": ["3"],
    }, follow_redirects=True)
    after = db_row("SELECT COUNT(*) AS n FROM industry_case")["n"]
    check("草稿已写入数据库", after == before + 1, f"{before} → {after}")
    new_case = db_row("SELECT * FROM industry_case ORDER BY case_id DESC LIMIT 1")
    check("新案例状态为草稿", new_case["status"] == "草稿", new_case["case_id"])
    mech_n = db_row("SELECT COUNT(*) AS n FROM case_mechanism WHERE case_id = ?",
                    (new_case["case_id"],))["n"]
    check("帮扶方式按 m:n 写入 2 条", mech_n == 2)

    r = c_member_b.get(f"/cases/{new_case['case_id']}")
    check("他人看不到队员甲的草稿", r.status_code == 404)
    r = c_member_b.post(f"/cases/{new_case['case_id']}/delete")
    check("他人不能删除该草稿", r.status_code in (403, 404))

    r = c_member.post(f"/cases/{new_case['case_id']}/submit", follow_redirects=True)
    st = db_row("SELECT status FROM industry_case WHERE case_id = ?",
                (new_case["case_id"],))["status"]
    check("提交后状态变待审核", st == "待审核", st)

    r = c_reviewer.post(f"/cases/{new_case['case_id']}/review",
                        data={"decision": "退回", "reason": ""}, follow_redirects=True)
    st = db_row("SELECT status FROM industry_case WHERE case_id = ?",
                (new_case["case_id"],))["status"]
    check("退回未写理由被拦截", st == "待审核", st)

    r = c_reviewer.post(f"/cases/{new_case['case_id']}/review",
                        data={"decision": "退回", "reason": "计划资金不能写成已支付"},
                        follow_redirects=True)
    st = db_row("SELECT status FROM industry_case WHERE case_id = ?",
                (new_case["case_id"],))["status"]
    check("退回后状态变退回补正", st == "退回补正", st)
    log_n = db_row("SELECT COUNT(*) AS n FROM audit_log WHERE case_id = ?",
                   (new_case["case_id"],))["n"]
    check("案例审核写入操作日志", log_n >= 2, f"{log_n} 条")

    print("\n[3] 任务：提交版本 → 审核通过 → 发布（事务）")
    r = c_member.post("/tasks/T-001/submit", data={
        "title": "金米村木耳证据整理 第1版",
        "note": "补齐帮扶方式与出处",
        "case_id": "",
    }, follow_redirects=True)
    task = db_row("SELECT state FROM field_task WHERE task_id='T-001'")
    ver = db_row("SELECT * FROM deliverable_version WHERE task_id='T-001' ORDER BY version_no DESC")
    check("提交后任务变待审核", task["state"] == "待审核", task["state"])
    check("生成了第 1 版提交记录", ver is not None and ver["version_no"] == 1)
    doc = db_row("SELECT source_kind FROM source_document WHERE document_id = ?",
                 (ver["document_id"],))
    check("版本挂了来源文档（提交材料）", doc["source_kind"] == "提交材料")

    r = c_member_b.post("/tasks/T-001/submit", data={"title": "越权", "note": "越权"})
    check("非受派成员不能提交（可见范围外按不存在处理）",
          r.status_code in (403, 404), f"HTTP {r.status_code}")

    r = c_reviewer.post("/tasks/T-001/review",
                        data={"decision": "通过", "reason": "来源与计划口径已核对"},
                        follow_redirects=True)
    task = db_row("SELECT state FROM field_task WHERE task_id='T-001'")
    check("审核通过后任务已完成", task["state"] == "已完成", task["state"])
    rev = db_row("SELECT * FROM review_action ORDER BY review_id DESC LIMIT 1")
    check("审核动作已入库", rev["decision"] == "通过")

    r = c_leader.post("/tasks/T-001/publish", follow_redirects=True)
    task = db_row("SELECT state FROM field_task WHERE task_id='T-001'")
    check("队长发布后状态已发布", task["state"] == "已发布", task["state"])

    r = c_member.post("/tasks/T-001/publish")
    check("队员不能发布", r.status_code == 403)

    print("\n[4] 数据库层约束")
    try:
        v = db_row("SELECT version_id, submitted_by FROM deliverable_version"
                   " WHERE task_id='T-001' ORDER BY version_no DESC LIMIT 1")
        db_exec("INSERT INTO review_action(version_id, reviewer_id, decision, reason, acted_at)"
                " VALUES (?,?, '通过', '自审测试', '2026-11-16 23:00')",
                (v["version_id"], v["submitted_by"]))
        check("触发器阻止自审", False, "竟然插入成功")
    except sqlite3.IntegrityError as exc:
        check("触发器阻止自审", "submitter cannot review own version" in str(exc), str(exc)[:40])

    try:
        v = db_row("SELECT version_id FROM deliverable_version WHERE task_id='T-001' ORDER BY version_no DESC LIMIT 1")
        db_exec("INSERT INTO review_action(version_id, reviewer_id, decision, reason, acted_at)"
                " VALUES (?, 5, '退回', '   ', '2026-11-16 23:00')", (v["version_id"],))
        check("CHECK 阻止空理由退回", False, "竟然插入成功")
    except sqlite3.IntegrityError:
        check("CHECK 阻止空理由退回", True)

    try:
        db_exec("INSERT INTO industry_case(case_id, county_id, title, industry,"
                " claim_summary, status, data_kind, owner_id)"
                " VALUES ('C-999', 290, '非法状态', '测试', '测试', '乱写', '课程模拟', 3)")
        check("CHECK 阻止非法案例状态", False, "竟然插入成功")
    except sqlite3.IntegrityError:
        check("CHECK 阻止非法案例状态", True)

    try:
        db_exec("INSERT INTO task_assignment(task_id, user_id, is_lead) VALUES ('T-002', 4, 1)")
        check("部分唯一索引阻止第二负责人", False, "竟然插入成功")
    except sqlite3.IntegrityError:
        check("部分唯一索引阻止第二负责人", True)

    print("\n[5] 权限可见范围")
    r = c_public.get("/cases")
    html = r.get_data(as_text=True)
    check("公众看不到未发布案例",
          new_case["case_id"] not in html and "C-006" not in html,
          f"草稿 {new_case['case_id']} / 退回 C-006 均不可见")
    check("公众能看到已发布案例", "C-003" in html)
    r = c_public.get("/tasks")
    check("公众看不到任务", "T-001" not in r.get_data(as_text=True))

    print("\n[6] 统计查询")
    r = c_public.get("/stats")
    html = r.get_data(as_text=True)
    check("双方式案例查询命中 C-003", "C-003" in html)
    check("金额核对显示 0 处不一致", "0 处不一致" in html)
    check("计划资金合计 19518", "19518" in html.replace(",", ""))

    print("\n" + "=" * 60)
    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print(f"结果：{passed}/{total} 通过")
    for ok, name, detail in results:
        if not ok:
            print(f"  未通过：{name} {detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
