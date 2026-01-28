from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional


def find_latest_sqlite_db(run_dir: str) -> Optional[str]:
    root = os.path.join(run_dir, "datacache")
    best_path: Optional[str] = None
    best_mtime = -1.0
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.startswith("proj_db_") and name.endswith(".db"):
                p = os.path.join(dirpath, name)
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                if m > best_mtime:
                    best_mtime = m
                    best_path = p
    return best_path


def read_dbtask_rows(db_path: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, stage, status, content, result_path, error_info, created_at, updated_at FROM dbtask ORDER BY updated_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def resolve_container_result_path(run_dir: str, result_path: str) -> Optional[str]:
    if not result_path:
        return None

    rp = result_path.strip()
    datacache_prefixes = [
        "./agent-service/datacache/",
        "agent-service/datacache/",
        "/home/guv/AI_Scientist/agent-service/datacache/",
    ]
    for pref in datacache_prefixes:
        if rp.startswith(pref):
            rel = rp[len(pref) :]
            return os.path.join(run_dir, "datacache", rel)

    if rp.startswith("./"):
        rp = rp[2:]

    candidate = os.path.join(run_dir, rp)
    if os.path.exists(candidate):
        return candidate

    return None


def list_artifacts(run_dir: str) -> List[Dict[str, str]]:
    artifacts: List[Dict[str, str]] = []

    logs_stdout = os.path.join(run_dir, "logs", "stdout.log")
    if os.path.exists(logs_stdout):
        artifacts.append({"kind": "log", "path": os.path.relpath(logs_stdout, run_dir)})

    db_path = find_latest_sqlite_db(run_dir)
    if db_path and os.path.exists(db_path):
        artifacts.append({"kind": "db", "path": os.path.relpath(db_path, run_dir)})

    if db_path:
        for row in read_dbtask_rows(db_path):
            rp = row.get("result_path")
            resolved = resolve_container_result_path(run_dir, str(rp)) if rp else None
            if resolved and os.path.exists(resolved):
                artifacts.append(
                    {
                        "kind": "md",
                        "stage": str(row.get("stage") or ""),
                        "task_id": str(row.get("id") or ""),
                        "path": os.path.relpath(resolved, run_dir),
                    }
                )

    extra_roots = [
        os.path.join(run_dir, "datacache"),
    ]
    for root in extra_roots:
        for sub in ["code", "experiment", "scripts"]:
            for dirpath, dirnames, _ in os.walk(root):
                if os.path.basename(dirpath) == sub:
                    artifacts.append({"kind": "dir", "path": os.path.relpath(dirpath, run_dir)})
                    dirnames[:] = []

    seen = set()
    deduped: List[Dict[str, str]] = []
    for a in artifacts:
        key = a.get("path", "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(a)
    return deduped

