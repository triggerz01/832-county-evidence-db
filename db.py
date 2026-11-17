"""数据库访问层：连接管理、查询助手、事务上下文。

所有 SQL 都在服务端执行，模板层不接触数据库。
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

DB_PATH = Path(os.environ.get("DB_PATH") or
               (Path(__file__).resolve().parent / "832_research_sample.sqlite"))


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query(sql: str, args=()) -> list[sqlite3.Row]:
    return get_db().execute(sql, args).fetchall()


def query_one(sql: str, args=()):
    return get_db().execute(sql, args).fetchone()


def scalar(sql: str, args=()):
    row = get_db().execute(sql, args).fetchone()
    return None if row is None else row[0]


def execute(sql: str, args=()) -> int:
    cur = get_db().execute(sql, args)
    return cur.lastrowid


@contextmanager
def transaction():
    """把多条写操作包成一个事务；出错整体回滚。"""
    conn = get_db()
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def write_log(conn, actor_id: int, task_id, action: str, acted_at: str, case_id=None):
    conn.execute(
        "INSERT INTO audit_log(actor_id, task_id, case_id, action, acted_at)"
        " VALUES (?,?,?,?,?)",
        (actor_id, task_id, case_id, action, acted_at),
    )


def init_app(app):
    app.teardown_appcontext(close_db)
