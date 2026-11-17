"""Build a source-labelled SQLite sample for the 832 database design.

Run once in this directory. Existing databases are never overwritten.
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "832_research_sample.sqlite"
if DB.exists():
    raise SystemExit(f"Database already exists; refusing to overwrite: {DB}")

reports = json.loads((ROOT / "ruc_832_public_reports.json").read_text(encoding="utf-8"))
audit = json.loads((ROOT / "county_source_audit.json").read_text(encoding="utf-8"))
projects = json.loads((ROOT / "official_project_rows.json").read_text(encoding="utf-8"))
schema = (ROOT / "832_schema.sql").read_text(encoding="utf-8")

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript(schema)
cur = conn.cursor()


def county_id(province: str, name: str) -> int:
    cur.execute(
        "INSERT OR IGNORE INTO county(province_raw,county_name_raw) VALUES (?,?)",
        (province, name),
    )
    return cur.execute(
        "SELECT county_id FROM county WHERE province_raw=? AND county_name_raw=?",
        (province, name),
    ).fetchone()[0]


def document_id(url: str, publisher: str, title: str, kind: str, external_id=None) -> int:
    cur.execute(
        """INSERT OR IGNORE INTO source_document
           (external_id,url,publisher,title,source_kind,checked_on)
           VALUES (?,?,?,?,?,'2026-10-29')""",
        (external_id, url, publisher, title, kind),
    )
    return cur.execute("SELECT document_id FROM source_document WHERE url=?", (url,)).fetchone()[0]


for item in reports:
    cid = county_id(item["province"], item["county"])
    did = document_id(item["url"], "中国人民大学应用经济学院", item["title"], "公开逐县报道")
    cur.execute(
        "INSERT INTO public_report(document_id,county_id,published_date) VALUES (?,?,?)",
        (did, cid, item["date"]),
    )

source_by_external_id = {}
for item in audit["sources"]:
    source_by_external_id[item["id"]] = document_id(
        item["url"], item["publisher"], item["title"], item["data_layer"], item["id"]
    )

RUC_ZS = "https://ae.ruc.edu.cn/xwzx/xydt/c9da52ef58f847e9b1a06c72c6428539.htm"
RUC_HQ = "https://ae.ruc.edu.cn/xwzx/xydt/fba7a54b0346410884e7eee36bd3bbc7.htm"
LS_PAGE = "https://www.laishui.gov.cn/index.php?a=show&c=index&catid=118&id=16947&m=content"
zs_report_id = cur.execute(
    "SELECT report_id FROM public_report WHERE document_id=(SELECT document_id FROM source_document WHERE url=?)",
    (RUC_ZS,),
).fetchone()[0]
people = [
    ("李正森", "金米村党支部书记", "报道记载对木耳菌包认领激励机制的访谈。"),
    ("王玉峰", "柞水县农业农村局局长", "报道访谈掠影图注。"),
    ("吴芳雯", "柞水县人大常委会副主任", "报道访谈掠影图注。"),
    ("周建波", "柞水县下梁镇党委书记", "报道访谈掠影图注。"),
]
cur.executemany(
    "INSERT INTO person_mention(report_id,person_name,role_text,context_summary) VALUES (?,?,?,?)",
    [(zs_report_id, *person) for person in people],
)

cur.execute("INSERT INTO team(team_id,team_name,data_kind) VALUES (1,'832 课程演示调研队','课程模拟')")
users = [
    (1, "管理员", "admin"),
    (2, "队长", "leader"),
    (3, "队员甲", "member"),
    (4, "队员乙", "member"),
    (5, "审核员", "reviewer"),
    (6, "研究员", "researcher"),
]
cur.executemany(
    "INSERT INTO user_account(user_id,team_id,display_name,role,data_kind) VALUES (?,1,?,?,'课程模拟')",
    users,
)

tasks = [
    ("T-001", "陕西", "柞水县", "核对金米村木耳案例的帮扶方式与出处", "案例报告", "2026-10-25", "已分配", 3),
    ("T-002", "安徽", "霍邱县", "整理城西湖乡莲藕基地的土地流转与就业证据", "资料包", "2026-11-02", "待审核", 4),
    ("T-003", "河北", "涞水县", "区分农特产品批发市场计划资金与实际成效", "案例报告", "2026-11-08", "退回补正", 3),
    ("T-004", "陕西", "柞水县", "整理 2024 年项目库与绩效目标的原表行", "资料包", "2026-11-05", "已完成", 4),
    ("T-005", "安徽", "霍邱县", "发布忠旭雨衣帮扶车间公开案例", "新闻速递", "2026-10-27", "已发布", 4),
]
for tid, province, name, topic, kind, due, state, assignee in tasks:
    cur.execute(
        """INSERT INTO field_task
           (task_id,county_id,topic,required_kind,due_at,state,created_by,data_kind)
           VALUES (?,?,?,?,?,?,2,'课程模拟')""",
        (tid, county_id(province, name), topic, kind, due, state),
    )
    cur.execute(
        "INSERT INTO task_assignment(task_id,user_id,is_lead) VALUES (?,?,1)",
        (tid, assignee),
    )
    cur.execute(
        "INSERT INTO audit_log(actor_id,task_id,action,acted_at) VALUES (2,?,'创建并指派','2026-10-22')",
        (tid,),
    )

cases = [
    ("C-001", "陕西", "柞水县", None, "金米村木耳产业带动农户", "木耳", "公开报道明确记载金米村将木耳大棚和菌包认领到户，并推行借袋还耳、借棚还耳模式。", "已发布", "公开报道整理", None, RUC_ZS, "金米村木耳段", ["借袋还耳", "借棚还耳", "菌包认领"]),
    ("C-002", "陕西", "柞水县", None, "柞水县康养民宿产业的增收方式", "乡村旅游", "报道在朱家湾村调研后介绍柞水县整体民宿运营模式，包括房屋租赁、入股分红和就地务工。", "已发布", "公开报道整理", None, RUC_ZS, "柞水县民宿产业段", ["房屋租赁", "入股分红", "就地务工"]),
    ("C-003", "安徽", "霍邱县", None, "城西湖乡莲藕基地带动农户", "莲藕", "报道记录莲藕基地以土地流转与就业等方式带动农户，不能自动对应政府加工项目。", "已发布", "公开报道整理", None, RUC_HQ, "城西湖乡莲藕基地段", ["土地流转", "就业", "企业帮扶", "旅游带动"]),
    ("C-004", "安徽", "霍邱县", None, "牧翔禽业的养殖户协作模式", "禽业", "报道描述公司、合作社、基地与养殖户的协作模式。", "已发布", "公开报道整理", None, RUC_HQ, "牧翔禽业段", ["合作社协作", "供苗服务", "统一销售"]),
    ("C-005", "安徽", "霍邱县", None, "忠旭雨衣帮扶车间就业", "制造业", "报道描述帮扶车间提供岗位，并设助学金。", "已发布", "公开报道整理", None, RUC_HQ, "忠旭雨衣段", ["就业", "帮扶车间", "教育资助"]),
    ("C-006", "河北", "涞水县", "T-003", "涞水农特产品市场的村集体资产安排", "农产品流通", "年度计划写明项目资金分年度安排，资产计划确权到全县 284 个村集体；不得写成已支付或实际收益。", "退回补正", "课程模拟", 3, LS_PAGE, "年度计划市场项目段", ["村集体资产", "产业配套"]),
]
for case in cases:
    cid, province, name, task_id, title, industry, claim, status, kind, owner, url, locator, modes = case
    cur.execute(
        """INSERT INTO industry_case
           (case_id,county_id,task_id,title,industry,claim_summary,status,data_kind,owner_id)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (cid, county_id(province, name), task_id, title, industry, claim, status, kind, owner),
    )
    did = cur.execute("SELECT document_id FROM source_document WHERE url=?", (url,)).fetchone()[0]
    cur.execute(
        "INSERT INTO source_excerpt(document_id,locator,summary) VALUES (?,?,?)",
        (did, locator, claim),
    )
    cur.execute(
        "INSERT INTO case_evidence(case_id,excerpt_id) VALUES (?,?)",
        (cid, cur.lastrowid),
    )
    for mode in modes:
        cur.execute("INSERT OR IGNORE INTO mechanism(name) VALUES (?)", (mode,))
        mid = cur.execute("SELECT mechanism_id FROM mechanism WHERE name=?", (mode,)).fetchone()[0]
        cur.execute("INSERT INTO case_mechanism(case_id,mechanism_id) VALUES (?,?)", (cid, mid))

deliverables = [
    ("T-002", "资料包", "城西湖乡莲藕基地调研材料", RUC_HQ, None, "依据公开报道整理莲藕基地的两种帮扶方式。", 4, "2026-10-27"),
    ("T-003", "案例报告", "涞水农特产品市场资料核对", LS_PAGE, "C-006", "整理 2024 年项目计划，待补充成效来源。", 3, "2026-10-26"),
    ("T-004", "资料包", "柞水项目库来源行索引", next(s["url"] for s in audit["sources"] if s["id"] == "zs_project_library_2024"), None, "保留项目库行号，预算均为计划值。", 4, "2026-10-27"),
    ("T-005", "新闻速递", "忠旭雨衣帮扶车间案例", RUC_HQ, None, "按照公开报道整理，已在演示流程中审核发布。", 4, "2026-10-26"),
]
version_ids = {}
for tid, kind, title, url, case_id, note, member_id, date in deliverables:
    did = cur.execute("SELECT document_id FROM source_document WHERE url=?", (url,)).fetchone()[0]
    cur.execute(
        """INSERT INTO deliverable_version
           (task_id,version_no,kind,title,document_id,case_id,note,submitted_by,submitted_at)
           VALUES (?,1,?,?,?,?,?,?,?)""",
        (tid, kind, title, did, case_id, note, member_id, date),
    )
    version_ids[tid] = cur.lastrowid
    cur.execute(
        "INSERT INTO audit_log(actor_id,task_id,action,acted_at) VALUES (?,?,'提交第 1 版',?)",
        (member_id, tid, date),
    )
for tid, decision, reason, date in [
    ("T-003", "退回", "计划资金不能写成已支付；请补充评价来源或改为计划口径。", "2026-10-28"),
    ("T-004", "通过", "来源和计划口径已核对。", "2026-10-28"),
    ("T-005", "通过", "已核对公开报道。", "2026-10-27"),
]:
    cur.execute(
        "INSERT INTO review_action(version_id,reviewer_id,decision,reason,acted_at) VALUES (?,5,?,?,?)",
        (version_ids[tid], decision, reason, date),
    )
    cur.execute(
        "INSERT INTO audit_log(actor_id,task_id,action,acted_at) VALUES (5,?,?,?)",
        (tid, decision, date),
    )

for example in audit["verified_examples"]:
    province = {"柞水县": "陕西", "霍邱县": "安徽", "涞水县": "河北"}[example["county"]]
    cur.execute(
        """INSERT INTO evidence_issue
           (issue_id,county_id,project_name_raw,facts_json,database_use,do_not_infer)
           VALUES (?,?,?,?,?,?)""",
        (
            example["id"],
            county_id(province, example["county"]),
            example["project_name"],
            json.dumps(example["facts"], ensure_ascii=False),
            example["database_use"],
            example["do_not_infer"],
        ),
    )
    for source_id in example["source_ids"]:
        cur.execute(
            "INSERT INTO evidence_issue_source(issue_id,document_id) VALUES (?,?)",
            (example["id"], source_by_external_id[source_id]),
        )

laishui = county_id("河北", "涞水县")
xlsx_document_id = cur.execute(
    "SELECT document_id FROM source_document WHERE url=?",
    (projects["source_documents"][0]["url"],),
).fetchone()[0]
for project in projects["projects"]:
    cur.execute(
        """INSERT INTO government_project
           (project_id,county_id,plan_year,project_name,category,html_project_no,xlsx_project_no)
           VALUES (?,?,?,?,?,?,?)""",
        (
            project["project_id"], laishui, project["plan_year"], project["project_name"],
            project["category"], project["html_project_no"], project["xlsx_project_no"],
        ),
    )
    cur.execute(
        """INSERT INTO project_snapshot
           (project_id,document_id,snapshot_kind,version_label,budget_wan)
           VALUES (?,?,'年度计划','涞水2024县政府计划',?)""",
        (project["project_id"], xlsx_document_id, project["planned_2024_funding_wan"]),
    )
for row in projects["project_location_rows"]:
    cur.execute(
        """INSERT INTO project_location
           (project_id,document_id,xlsx_row,implementation_location_raw,planned_2024_funding_wan)
           VALUES (?,?,?,?,?)""",
        (
            row["project_id"], xlsx_document_id, row["xlsx_row"],
            row["implementation_location_raw"], row["planned_2024_funding_wan"],
        ),
    )

conn.commit()
assert not conn.execute("PRAGMA foreign_key_check").fetchall()
for table, expected in [
    ("public_report", 297), ("government_project", 43), ("project_location", 158),
    ("person_mention", 4), ("industry_case", 6), ("field_task", 5), ("evidence_issue", 8),
]:
    actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    assert actual == expected, (table, actual, expected)
funding = conn.execute("SELECT SUM(budget_wan) FROM project_snapshot").fetchone()[0]
assert abs(funding - 19518) < 1e-6, funding
print("SQLite sample created:", DB)
print("297 reports; 43 projects; 158 project-location rows; 6 cases (5 public, 1 demo); 5 demo tasks; 8 source issues")
print("2024 plan funding:", funding, "万元")
conn.close()
