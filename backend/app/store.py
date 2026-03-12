from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .settings import settings


def _utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _db_path() -> str:
    os.makedirs(settings.data_dir, exist_ok=True)
    return os.path.join(settings.data_dir, "webapp.sqlite3")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              salt TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'user',
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompt_sets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS prompt_versions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              prompt_set_id INTEGER NOT NULL,
              version INTEGER NOT NULL,
              notes TEXT,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(prompt_set_id, version),
              FOREIGN KEY(prompt_set_id) REFERENCES prompt_sets(id)
            );

            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              yaml_filename TEXT NOT NULL,
              project_id TEXT NOT NULL,
              project_name TEXT,
              prompt_version_id INTEGER,
              workspace_dir TEXT NOT NULL,
              container_id TEXT,
              exit_code INTEGER,
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(prompt_version_id) REFERENCES prompt_versions(id)
            );
            """
        )
        try:
            conn.execute("ALTER TABLE runs ADD COLUMN project_name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass
        conn.execute("UPDATE users SET role='user' WHERE role IS NULL")
        conn.commit()
    finally:
        conn.close()


@dataclass(frozen=True)
class User:
    id: int
    username: str
    role: str
    created_at: str


def create_user(username: str, password_hash: str, salt: str, role: str = "user") -> User:
    conn = get_conn()
    try:
        created_at = _utc_iso()
        cur = conn.execute(
            "INSERT INTO users(username, password_hash, salt, role, created_at) VALUES(?,?,?,?,?)",
            (username, password_hash, salt, role, created_at),
        )
        conn.commit()
        return User(id=cur.lastrowid, username=username, role=role, created_at=created_at)
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if row is None:
            return None
        role = row["role"] if row["role"] else "user"
        return User(id=row["id"], username=row["username"], role=role, created_at=row["created_at"])
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[Tuple[User, str, str]]:
    """Returns (User, password_hash, salt) or None."""
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if row is None:
            return None
        role = row["role"] if row["role"] else "user"
        u = User(id=row["id"], username=row["username"], role=role, created_at=row["created_at"])
        return u, row["password_hash"], row["salt"]
    finally:
        conn.close()


def create_prompt_set(user_id: int, name: str) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO prompt_sets(user_id, name, created_at) VALUES(?,?,?)",
            (user_id, name, _utc_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_prompt_set(prompt_set_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM prompt_sets WHERE id=?", (prompt_set_id,))
        row = cur.fetchone()
        return dict(row) if row is not None else None
    finally:
        conn.close()


def list_prompt_sets(user_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT prompt_sets.*, users.username AS creator
            FROM prompt_sets
            JOIN users ON prompt_sets.user_id = users.id
            WHERE prompt_sets.user_id=?
            ORDER BY prompt_sets.id DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def list_prompt_sets_all() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT prompt_sets.*, users.username AS creator
            FROM prompt_sets
            JOIN users ON prompt_sets.user_id = users.id
            ORDER BY prompt_sets.id DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_prompt_version(prompt_set_id: int, notes: str, payload: Dict[str, Any]) -> Tuple[int, int]:
    conn = get_conn()
    try:
        # get next version
        cur = conn.execute(
            "SELECT MAX(version) FROM prompt_versions WHERE prompt_set_id=?", (prompt_set_id,)
        )
        row = cur.fetchone()
        next_ver = 1
        if row and row[0] is not None:
            next_ver = row[0] + 1

        payload_json = json.dumps(payload)
        cur = conn.execute(
            "INSERT INTO prompt_versions(prompt_set_id, version, notes, payload_json, created_at) VALUES(?,?,?,?,?)",
            (prompt_set_id, next_ver, notes, payload_json, _utc_iso()),
        )
        conn.commit()
        return cur.lastrowid, next_ver
    finally:
        conn.close()


def list_prompt_versions(prompt_set_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_set_id=? ORDER BY version DESC",
            (prompt_set_id,),
        )
        res = []
        for r in cur.fetchall():
            d = dict(r)
            d["payload"] = json.loads(d["payload_json"])
            del d["payload_json"]
            res.append(d)
        return res
    finally:
        conn.close()


def get_prompt_version(prompt_set_id: int, version: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_set_id=? AND version=?",
            (prompt_set_id, version),
        )
        r = cur.fetchone()
        if not r:
            return None
        d = dict(r)
        d["payload"] = json.loads(d["payload_json"])
        del d["payload_json"]
        return d
    finally:
        conn.close()


def get_prompt_version_by_id(pv_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM prompt_versions WHERE id=?", (pv_id,))
        r = cur.fetchone()
        if not r:
            return None
        d = dict(r)
        d["payload"] = json.loads(d["payload_json"])
        del d["payload_json"]
        return d
    finally:
        conn.close()


def create_run(
    user_id: int,
    yaml_filename: str,
    project_id: str,
    project_name: Optional[str],
    prompt_version_id: Optional[int],
    workspace_dir: str,
    run_id: Optional[str] = None,
) -> str:
    run_id = str(run_id or uuid.uuid4())
    conn = get_conn()
    try:
        now = _utc_iso()
        conn.execute(
            """INSERT INTO runs(
                 id, user_id, status, created_at, updated_at, 
                 yaml_filename, project_id, project_name, prompt_version_id, workspace_dir
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                user_id,
                "pending",
                now,
                now,
                yaml_filename,
                project_id,
                project_name,
                prompt_version_id,
                workspace_dir,
            ),
        )
        conn.commit()
        return run_id
    finally:
        conn.close()


def update_run_status(
    run_id: str, status: str, container_id: Optional[str] = None, exit_code: Optional[int] = None
) -> None:
    conn = get_conn()
    try:
        now = _utc_iso()
        updates = ["status=?, updated_at=?"]
        args: List[Any] = [status, now]
        if container_id is not None:
            updates.append("container_id=?")
            args.append(container_id)
        if exit_code is not None:
            updates.append("exit_code=?")
            args.append(exit_code)
        args.append(run_id)

        sql = f"UPDATE runs SET {', '.join(updates)} WHERE id=?"
        conn.execute(sql, tuple(args))
        conn.commit()
    finally:
        conn.close()


def delete_run(run_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM runs WHERE id=?", (run_id,))
        conn.commit()
    finally:
        conn.close()


def list_runs(user_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT runs.*, users.username AS creator
            FROM runs
            JOIN users ON runs.user_id = users.id
            WHERE runs.user_id=?
            ORDER BY runs.created_at DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def list_runs_all() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT runs.*, users.username AS creator
            FROM runs
            JOIN users ON runs.user_id = users.id
            ORDER BY runs.created_at DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,))
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def get_latest_run_by_project(user_id: int, project_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT * FROM runs WHERE user_id=? AND project_id=? ORDER BY created_at DESC LIMIT 1",
            (user_id, project_id),
        )
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def delete_prompt_set(prompt_set_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM prompt_versions WHERE prompt_set_id=?", (prompt_set_id,))
        conn.execute("DELETE FROM prompt_sets WHERE id=?", (prompt_set_id,))
        conn.commit()
    finally:
        conn.close()


def delete_prompt_version(prompt_set_id: int, version: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM prompt_versions WHERE prompt_set_id=? AND version=?",
            (prompt_set_id, version),
        )
        conn.commit()
    finally:
        conn.close()


def list_users() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def set_user_role(user_id: int, role: str) -> None:
    conn = get_conn()
    try:
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        conn.commit()
    finally:
        conn.close()


def get_run_status_counts(user_id: int) -> Dict[str, int]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM runs WHERE user_id=? GROUP BY status",
            (user_id,),
        )
        res: Dict[str, int] = {}
        for r in cur.fetchall():
            res[str(r["status"])] = int(r["cnt"])
        return res
    finally:
        conn.close()


def get_run_daily_counts(user_id: int, start_date: str) -> List[Tuple[str, int]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT substr(created_at, 1, 10) as day, COUNT(*) as cnt
            FROM runs
            WHERE user_id=? AND substr(created_at, 1, 10) >= ?
            GROUP BY day
            ORDER BY day
            """,
            (user_id, start_date),
        )
        return [(str(r["day"]), int(r["cnt"])) for r in cur.fetchall()]
    finally:
        conn.close()
