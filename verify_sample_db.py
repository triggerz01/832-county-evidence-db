"""Run the six source-backed SQL examples and check the course sample database."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
conn = sqlite3.connect(ROOT / "832_research_sample.sqlite")
queries = [q.strip() for q in (ROOT / "832_verified_queries.sql").read_text(encoding="utf-8").split(";") if q.strip()]
assert len(queries) == 6, len(queries)
results = [conn.execute(query).fetchall() for query in queries]
assert sum(count for _, count in results[0]) == 297
assert [row[0] for row in results[1]] == ["C-003"]
assert [row[0] for row in results[2]] == ["T-001"]
assert sum(row[1] for row in results[3]) == 43
assert abs(sum(row[2] for row in results[3]) - 19518) < 1e-6
assert results[4] == []
assert results[5] == [(295,)]
assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

version_id = conn.execute("SELECT version_id FROM deliverable_version WHERE task_id='T-003'").fetchone()[0]
try:
    conn.execute(
        "INSERT INTO review_action(version_id,reviewer_id,decision,reason,acted_at) VALUES (?,?,?,?,'2026-10-29')",
        (version_id, 3, "通过", "自审测试"),
    )
    raise AssertionError("Self-review trigger did not reject the insert")
except sqlite3.IntegrityError as error:
    assert "submitter cannot review own version" in str(error)
finally:
    conn.rollback()

print("PASS: 6 SQL queries; 297 reports; 43 projects; 19,518 万元; 295 unstructured reports")
print("PASS: case C-003 has both modes; T-001 is overdue; no amount mismatch; foreign keys and no-self-review trigger")
conn.close()
