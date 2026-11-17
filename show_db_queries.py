"""Print all six verified SQL result sets from the local SQLite sample."""

import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parent
sql_file = root / "832_verified_queries.sql"
database = root / "832_research_sample.sqlite"
queries = [q.strip() for q in sql_file.read_text(encoding="utf-8").split(";") if q.strip()]
assert len(queries) == 6

with sqlite3.connect(database) as connection:
    for number, query in enumerate(queries, 1):
        cursor = connection.execute(query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        print(f"\nQ{number} · {len(rows)} 行")
        print(" | ".join(columns))
        for row in rows:
            print(" | ".join("—" if value is None else str(value) for value in row))
        if not rows:
            print("（没有符合条件的记录）")
