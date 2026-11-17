"""给 832 样本库补齐后端需要的数据库对象（可重复执行）。

新增内容：
  1. 三个视图：已发布案例、任务进度、项目分类汇总
  2. 两个查询索引
  3. 六个演示账号的口令散列（pbkdf2）
这些对象同时写进了 832_schema.sql，保证"从零建库"和"增量迁移"结果一致。
"""

import sqlite3
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "832_research_sample.sqlite"
DEMO_PASSWORD = "832demo"

VIEWS = [
    ("v_published_case", """
CREATE VIEW IF NOT EXISTS v_published_case AS
SELECT ic.case_id, ic.title, c.province_raw, c.county_name_raw, ic.industry,
       (SELECT group_concat(m.name, '、')
          FROM case_mechanism cm JOIN mechanism m ON m.mechanism_id = cm.mechanism_id
         WHERE cm.case_id = ic.case_id) AS mechanisms,
       (SELECT COUNT(*) FROM case_evidence ce WHERE ce.case_id = ic.case_id) AS evidence_count
FROM industry_case ic
JOIN county c ON c.county_id = ic.county_id
WHERE ic.status = '已发布'
"""),
    ("v_task_progress", """
CREATE VIEW IF NOT EXISTS v_task_progress AS
SELECT t.task_id, t.topic, t.required_kind, t.due_at, t.state,
       c.province_raw, c.county_name_raw,
       (SELECT u.display_name
          FROM task_assignment a JOIN user_account u ON u.user_id = a.user_id
         WHERE a.task_id = t.task_id AND a.is_lead = 1) AS lead_name,
       (SELECT MAX(v.version_no) FROM deliverable_version v WHERE v.task_id = t.task_id) AS latest_no,
       (SELECT COUNT(*) FROM deliverable_version v WHERE v.task_id = t.task_id) AS version_count,
       (SELECT COUNT(*) FROM review_action r
          JOIN deliverable_version v ON v.version_id = r.version_id
         WHERE v.task_id = t.task_id) AS review_count
FROM field_task t
JOIN county c ON c.county_id = t.county_id
"""),
    ("v_project_category", """
CREATE VIEW IF NOT EXISTS v_project_category AS
SELECT gp.category, COUNT(DISTINCT gp.project_id) AS project_count,
       ROUND(SUM(ps.budget_wan), 6) AS planned_funding_wan
FROM government_project gp
JOIN project_snapshot ps ON ps.project_id = gp.project_id
WHERE gp.plan_year = 2024
  AND ps.snapshot_kind = '年度计划'
  AND ps.version_label = '涞水2024县政府计划'
GROUP BY gp.category
"""),
]

INDEXES = [
    ("idx_case_status", "CREATE INDEX IF NOT EXISTS idx_case_status ON industry_case(status, county_id)"),
    ("idx_task_state", "CREATE INDEX IF NOT EXISTS idx_task_state ON field_task(state, due_at)"),
    ("idx_version_task", "CREATE INDEX IF NOT EXISTS idx_version_task ON deliverable_version(task_id, version_no)"),
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"找不到样本库：{DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    for name, ddl in VIEWS:
        cur.execute(ddl)
        print(f"视图 {name} 就绪")
    for name, ddl in INDEXES:
        cur.execute(ddl)
        print(f"索引 {name} 就绪")

    columns = {row[1] for row in cur.execute("PRAGMA table_info(audit_log)")}
    if "case_id" not in columns:
        cur.execute(
            "ALTER TABLE audit_log ADD COLUMN case_id TEXT"
            " REFERENCES industry_case(case_id)"
        )
        print("audit_log.case_id 已补齐")

    cur.execute("SELECT user_id, display_name, password_hash FROM user_account ORDER BY user_id")
    rows = cur.fetchall()
    updated = 0
    for user_id, display_name, pwd in rows:
        if not pwd:
            cur.execute(
                "UPDATE user_account SET password_hash = ? WHERE user_id = ?",
                (generate_password_hash(DEMO_PASSWORD), user_id),
            )
            updated += 1
    conn.commit()

    print(f"账号口令已设置：{updated} 个（演示口令 {DEMO_PASSWORD}）")
    for table, in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ):
        n = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f"  {table:26s} {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
