"""生成测试用数据库副本并灌入覆盖各状态的测试数据。

用法：
    python make_test_data.py          # 首次生成 832_test_playground.sqlite
    python make_test_data.py --force  # 重新生成（丢弃所有测试改动）

特点：
    * 真实样本库 832_research_sample.sqlite 完全不动；
    * 测试数据带 TT- / TC- / urn:test: 前缀，一条 SQL 就能清干净；
    * 覆盖全部 6 种任务状态、5 种案例状态，含逾期、退回、多版本、待审、可发布。
"""

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "832_research_sample.sqlite"
DST = ROOT / "832_test_playground.sqlite"

TASKS = [
    # id, 县, 主题, 应交, 截止, 状态, 负责人, 提交人, 版本说明, 审核
    ("TT-001", "涞水县", "核对农特产品市场案例的村集体资产安排", "案例报告",
     "2026-12-05", "已分配", "队员甲", None, None, None),
    ("TT-002", "霍邱县", "补充莲藕深加工三期的资金证据", "资料包",
     "2026-12-08", "进行中", "队员乙", None, None, None),
    ("TT-003", "柞水县", "核对木耳项目绩效目标的口径差异", "案例报告",
     "2026-12-01", "待审核", "队员甲", "队员甲",
     "按年初、年中两份批复逐条列出口径差异", None),
    ("TT-004", "霍邱县", "补交屋顶光伏项目来源说明", "资料包",
     "2026-11-10", "退回补正", "队员乙", "队员乙",
     "首次提交，把计划资金写成了已支付", ("退回", "计划资金不能写成已支付；请改为计划口径并补充来源")),
    ("TT-005", "涞水县", "整理基础设施类项目的实施地点", "案例报告",
     "2026-11-05", "已完成", "队员甲", "队员甲",
     "按 16 个基础设施项目逐条对应实施地点", ("通过", "来源与口径已核对")),
    ("TT-006", "柞水县", "金米村木耳基地走访记录", "新闻速递",
     "2026-11-01", "已发布", "队员乙", "队员乙",
     "走访记录整理，含 4 位受访者说法", ("通过", "已核对公开报道，可对外")),
    ("TT-007", "霍邱县", "整理城西湖乡莲藕基地的用工记录", "案例报告",
     "2026-11-08", "已分配", "队员乙", None, None, None),
]

# 每个任务的提交时间。刻意与截止日错开，保证「逾期」判定与状态自洽：
#   TT-003 按期交（截止 12-01）、TT-004 迟交（截止 11-10 → 逾期）、
#   TT-005 / TT-006 均按期交，所以已完成的不会被误判成「逾期未交」。
SUBMIT_AT = {
    "TT-003": "2026-11-12 16:20",
    "TT-004": "2026-11-12 16:20",
    "TT-005": "2026-11-03 10:00",
    "TT-006": "2026-10-28 09:40",
}

CASES = [
    # id, 县, 标题, 产业, 说法, 状态, 性质, 负责人, 任务, 方式, 摘录序号
    ("TC-001", "涞水县", "农特产品批发市场的村集体资产安排", "农产品流通",
     "公开计划文件记载市场建设内容与计划资金，未记载实际收益与分红。",
     "草稿", "课程模拟", "队员甲", "TT-001", ["村集体资产", "房屋租赁"], 1),
    ("TC-002", "柞水县", "大寺沟村连翘种植的供苗与收购安排", "中药材",
     "公示材料记载规划面积与计划资金；收购价格与农户实际收入无公开数据。",
     "草稿", "公开报道整理", "队员乙", None, ["供苗服务", "统一销售"], 3),
    ("TC-003", "霍邱县", "稻虾共养的合作社统一供苗模式", "水稻",
     "报道称合作社统一供苗、订单收购，未给出农户亩均收益。",
     "待审核", "公开报道整理", "队员甲", None, ["合作社交作", "统一销售", "供苗服务"], 4),
    ("TC-004", "涞水县", "民宿旅游带动的房屋租赁与就地务工", "乡村旅游",
     "材料把计划接待量写成了实际接待量，需退回核对。",
     "退回补正", "课程模拟", "队员乙", None, ["旅游带动", "房屋租赁", "就地务工"], 5),
    ("TC-005", "霍邱县", "鹅产业的帮扶车间与订单收购", "禽业",
     "报道记载帮扶车间的用工规模与计件方式，未披露人均工资。",
     "已审核", "公开报道整理", "队员甲", None, ["帮扶车间", "企业帮扶"], 6),
    ("TC-006", "柞水县", "菌包认领到户的两种模式", "木耳",
     "报道明确记载借袋还耳、借棚还耳两种模式及认领规模。",
     "已发布", "公开报道整理", "队员甲", None, ["借袋还耳", "借棚还耳", "菌包认领"], 7),
    ("TC-007", "霍邱县", "柳编订单收购与居家就业", "制造业",
     "报道记载企业提供订单、农户居家编织，按件计酬。",
     "已发布", "公开报道整理", "队员乙", None, ["企业帮扶", "统一销售"], 8),
]

TEST_DOCS = [
    ("urn:test:notice:laishui-market", "涞水县乡村振兴局",
     "涞水县2024年度农特产品批发市场项目公示", "县级年度实施计划",
     "第2段", "项目计划资金 320 万元，建设地点为县城北环路，含交易大棚与冷链仓储。"),
    ("urn:test:notice:hq-lotus", "霍邱县农业农村局",
     "霍邱县城西湖乡莲藕深加工项目（三期）公示", "乡镇年度项目计划及联农带农目标",
     "第1段", "三期计划资金 480 万元，建设冷库与分拣线，计划带动务工岗位。"),
    ("urn:test:notice:zs-forsythia", "柞水县乡村振兴局",
     "柞水县凤凰镇大寺沟村连翘种植项目公示", "项目储备库与计划预算",
     "第3段", "项目计划 30 万元，规划连片种植 50 亩，配套供苗与技术服务。"),
    ("urn:test:report:hq-rice-shrimp", "中国人民大学应用经济学院",
     "霍邱县稻虾共养合作社带动农户（测试来源）", "公开逐县报道",
     "第4段", "合作社统一供苗、统一技术指导，成虾由合作社按订单收购。"),
    ("urn:test:notice:laishui-homestay", "涞水县文化和旅游局",
     "涞水县2024年度乡村旅游民宿改造项目公示", "县级年度实施计划",
     "第2段", "计划改造民宿 12 户、设床位 60 张；未记载实际接待量与农户实收租金。"),
    ("urn:test:report:hq-goose", "测试报道（霍邱鹅产业）",
     "霍邱县鹅产业帮扶车间的用工与计酬方式（测试来源）", "乡镇及企业年度成果报道",
     "第3段", "帮扶车间吸纳 46 人就业，按件计酬；报道未披露人均月收入。"),
    ("urn:test:report:zs-mushroom", "测试报道（柞水菌包）",
     "柞水县菌包认领到户的两种模式（测试来源）", "特色产业规模报道",
     "第2段", "借袋还耳每户认领 5000 袋，企业保底收购；借棚还耳由企业出棚、农户出工。"),
    ("urn:test:report:hq-willow", "测试报道（霍邱柳编）",
     "霍邱县柳编订单收购与居家编织（测试来源）", "乡镇及企业年度成果报道",
     "第4段", "企业提供订单与原料，农户居家编织、按件计酬，未记载年均收入。"),
]


def cleanup(cur):
    cur.execute("DELETE FROM review_action WHERE version_id IN"
                " (SELECT version_id FROM deliverable_version WHERE task_id LIKE 'TT-%')")
    cur.execute("DELETE FROM deliverable_version WHERE task_id LIKE 'TT-%'")
    cur.execute("DELETE FROM task_assignment WHERE task_id LIKE 'TT-%'")
    cur.execute("DELETE FROM field_task WHERE task_id LIKE 'TT-%'")
    cur.execute("DELETE FROM audit_log WHERE task_id LIKE 'TT-%' OR case_id LIKE 'TC-%'")
    cur.execute("DELETE FROM case_mechanism WHERE case_id LIKE 'TC-%'")
    cur.execute("DELETE FROM case_evidence WHERE case_id LIKE 'TC-%'")
    cur.execute("DELETE FROM industry_case WHERE case_id LIKE 'TC-%'")
    cur.execute("DELETE FROM source_excerpt WHERE document_id IN"
                " (SELECT document_id FROM source_document"
                "   WHERE url LIKE 'urn:test:%' OR url LIKE 'urn:deliverable:TT-%')")
    cur.execute("DELETE FROM source_document"
                " WHERE url LIKE 'urn:test:%' OR url LIKE 'urn:deliverable:TT-%'")


def main() -> int:
    force = "--force" in sys.argv
    if DST.exists() and not force:
        print(f"测试库已存在：{DST.name}\n如需重来请加 --force（会丢弃你的测试改动）")
        return 0
    if not SRC.exists():
        print("找不到样本库，请先运行 build_sample_db.py", file=sys.stderr)
        return 1

    shutil.copyfile(SRC, DST)
    conn = sqlite3.connect(DST)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    cleanup(cur)

    uid = {r["display_name"]: r["user_id"]
           for r in cur.execute("SELECT user_id, display_name FROM user_account")}
    cid = {r["county_name_raw"]: r["county_id"]
           for r in cur.execute("SELECT county_id, county_name_raw FROM county")}
    mid = {r["name"]: r["mechanism_id"]
           for r in cur.execute("SELECT mechanism_id, name FROM mechanism")}

    # 测试来源文档与摘录
    excerpt_ids = []
    for url, pub, title, kind, loc, summary in TEST_DOCS:
        did = cur.execute(
            "INSERT INTO source_document(external_id,url,publisher,title,source_kind,checked_on)"
            " VALUES (NULL,?,?,?,?, '2026-11-10')", (url, pub, title, kind)).lastrowid
        excerpt_ids.append(cur.execute(
            "INSERT INTO source_excerpt(document_id,locator,summary) VALUES (?,?,?)",
            (did, loc, summary)).lastrowid)

    # 任务与版本、审核、日志
    now = "2026-11-16 21:00"
    for tid, county, topic, kind, due, state, owner, submitter, note, review in TASKS:
        cur.execute(
            "INSERT INTO field_task(task_id,county_id,topic,required_kind,due_at,state,"
            "created_by,data_kind) VALUES (?,?,?,?,?,?,?,'课程模拟')",
            (tid, cid[county], topic, kind, due, state, uid["队长"]))
        cur.execute("INSERT INTO task_assignment(task_id,user_id,is_lead) VALUES (?,?,1)",
                    (tid, uid[owner]))
        cur.execute("INSERT INTO audit_log(actor_id,task_id,action,acted_at) VALUES (?,?,?,?)",
                    (uid["队长"], tid, f"创建并指派 {tid}", "2026-11-01 09:00"))
        if not submitter:
            continue
        no = 1
        sub_at = SUBMIT_AT.get(tid, "2026-11-12 16:20")
        doc = cur.execute(
            "INSERT INTO source_document(external_id,url,publisher,title,source_kind,checked_on)"
            " VALUES (NULL,?,?,?, '提交材料', '2026-11-12')",
            (f"urn:deliverable:{tid}:{no}", submitter, f"{topic}（第{no}版）")).lastrowid
        vid = cur.execute(
            "INSERT INTO deliverable_version(task_id,version_no,kind,title,document_id,"
            "case_id,note,submitted_by,submitted_at) VALUES (?,?,?,?,?,NULL,?,?,?)",
            (tid, no, kind, f"{topic}（第{no}版）", doc, note,
             uid[submitter], sub_at)).lastrowid
        cur.execute("INSERT INTO audit_log(actor_id,task_id,action,acted_at) VALUES (?,?,?,?)",
                    (uid[submitter], tid, f"提交第 {no} 版 {kind}", sub_at))
        if review:
            decision, reason = review
            cur.execute(
                "INSERT INTO review_action(version_id,reviewer_id,decision,reason,acted_at)"
                " VALUES (?,?,?,?,?)",
                (vid, uid["审核员"], decision, reason, "2026-11-13 10:05"))
            cur.execute("INSERT INTO audit_log(actor_id,task_id,action,acted_at)"
                        " VALUES (?,?,?,?)",
                        (uid["审核员"], tid, f"审核第 {no} 版：{decision}", "2026-11-13 10:05"))
            if state == "已发布":
                cur.execute("INSERT INTO audit_log(actor_id,task_id,action,acted_at)"
                            " VALUES (?,?,?,?)",
                            (uid["队长"], tid, "发布成果", "2026-11-14 09:30"))

    # 案例
    for (case_id, county, title, industry, claim, status, kind, owner,
         task, mechs, ex_idx) in CASES:
        cur.execute(
            "INSERT INTO industry_case(case_id,county_id,task_id,title,industry,"
            "claim_summary,status,data_kind,owner_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (case_id, cid[county], task, title, industry, claim, status, kind, uid[owner]))
        for name in mechs:
            if name in mid:
                cur.execute("INSERT INTO case_mechanism(case_id,mechanism_id) VALUES (?,?)",
                            (case_id, mid[name]))
        if ex_idx is not None:
            cur.execute("INSERT INTO case_evidence(case_id,excerpt_id) VALUES (?,?)",
                        (case_id, excerpt_ids[ex_idx - 1]))
        cur.execute("INSERT INTO audit_log(actor_id,case_id,action,acted_at) VALUES (?,?,?,?)",
                    (uid[owner], case_id, f"新建案例草稿 {case_id}", "2026-11-11 14:00"))
        if status in ("待审核", "已审核", "已发布", "退回补正"):
            cur.execute("INSERT INTO audit_log(actor_id,case_id,action,acted_at)"
                        " VALUES (?,?,?,?)",
                        (uid[owner], case_id, f"提交案例待审 {case_id}", "2026-11-12 11:00"))
        if status == "退回补正":
            cur.execute("INSERT INTO audit_log(actor_id,case_id,action,acted_at)"
                        " VALUES (?,?,?,?)",
                        (uid["审核员"], case_id,
                         f"案例审核退回 {case_id}：把计划接待量写成了实际接待量", "2026-11-13 15:40"))
        if status in ("已审核", "已发布"):
            cur.execute("INSERT INTO audit_log(actor_id,case_id,action,acted_at)"
                        " VALUES (?,?,?,?)",
                        (uid["审核员"], case_id, f"案例审核通过 {case_id}：来源已核对", "2026-11-13 15:40"))
        if status == "已发布":
            cur.execute("INSERT INTO audit_log(actor_id,case_id,action,acted_at)"
                        " VALUES (?,?,?,?)",
                        (uid["队长"], case_id, f"发布案例 {case_id}", "2026-11-14 09:35"))

    conn.commit()

    print(f"测试库已生成：{DST.name}（源库 {SRC.name} 未被改动）\n")
    print("任务")
    for r in cur.execute(
            "SELECT v.task_id, v.county_name_raw, v.state, v.lead_name, v.due_at"
            " FROM v_task_progress v WHERE v.task_id LIKE 'TT-%' ORDER BY v.task_id"):
        print(f"  {r['task_id']}  {r['county_name_raw']:<5} {r['state']:<5}"
              f" {r['lead_name']:<4} 截止 {r['due_at']}")
    print("\n案例")
    for r in cur.execute(
            "SELECT case_id, county_name_raw, title, status, data_kind FROM "
            "(SELECT c.case_id, n.county_name_raw, c.title, c.status, c.data_kind"
            " FROM industry_case c JOIN county n ON n.county_id=c.county_id"
            " WHERE c.case_id LIKE 'TC-%') ORDER BY case_id"):
        print(f"  {r[0]}  {r[1]:<5} {r[3]:<5} {r[4]:<6} {r[2]}")
    total_task = cur.execute("SELECT COUNT(*) FROM field_task").fetchone()[0]
    total_case = cur.execute("SELECT COUNT(*) FROM industry_case").fetchone()[0]
    overdue = cur.execute(
        "SELECT group_concat(v.task_id, ' ') FROM v_task_progress v WHERE v.due_at < '2026-11-17'"
        " AND NOT EXISTS (SELECT 1 FROM deliverable_version d WHERE d.task_id=v.task_id"
        "                 AND d.kind=v.required_kind"
        "                 AND substr(d.submitted_at,1,10) <= v.due_at)").fetchone()[0]
    print(f"\n合计：任务 {total_task} 个、案例 {total_case} 个")
    print(f"逾期（截止日已过且无按期提交）：{overdue}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
