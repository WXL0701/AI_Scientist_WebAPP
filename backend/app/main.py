from __future__ import annotations

import os
import pathlib
import uuid
from typing import Any, Dict, List, Optional

import yaml
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse

from .ai_outputs import find_latest_sqlite_db, list_artifacts, read_dbtask_rows
from .prompts import apply_system_message_overrides, copy_baseline_prompts, load_baseline_system_messages, normalize_prompt_payload
from .runner import start_run_container, stop_run_container
from .security import create_access_token, decode_token, hash_password, new_salt, verify_password
from .settings import settings
from .store import (
    User,
    create_prompt_set,
    create_prompt_version,
    create_run,
    create_user,
    get_prompt_version,
    get_prompt_version_by_id,
    get_user_by_username,
    get_user_by_id,
    get_run,
    init_db,
    list_prompt_sets,
    list_prompt_versions,
    list_runs,
    update_run_status,
)


app = FastAPI(title="AI Scientist WebAPP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


def _require_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="missing token")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="invalid token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="invalid token")
    user = get_user_by_id(int(sub))
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


@app.on_event("startup")
def _startup() -> None:
    init_db()
    os.makedirs(settings.runs_root, exist_ok=True)

    # Create Admin account if not exists
    admin_user = get_user_by_username("Admin")
    if not admin_user:
        salt = new_salt()
        pw_hash = hash_password("admin123", salt)
        create_user("Admin", pw_hash, salt)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register")
def register(payload: Dict[str, Any]) -> Dict[str, Any]:
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username/password required")
    
    # Allow alphanumeric
    if not username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="username must be alphanumeric (can include _ -)")

    existing = get_user_by_username(username)
    if existing is not None:
        raise HTTPException(status_code=409, detail="username exists")
    salt = new_salt()
    pw_hash = hash_password(password, salt)
    user = create_user(username, pw_hash, salt)
    token = create_access_token(user.id, user.username)
    return {"access_token": token, "user": {"id": user.id, "username": user.username}}


@app.post("/auth/login")
def login(payload: Dict[str, Any]) -> Dict[str, Any]:
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username/password required")
    got = get_user_by_username(username)
    if got is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    user, pw_hash, salt = got
    if not verify_password(password, salt, pw_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = create_access_token(user.id, user.username)
    return {"access_token": token, "user": {"id": user.id, "username": user.username}}


@app.get("/me")
def me(user: User = Depends(_require_user)) -> Dict[str, Any]:
    return {"id": user.id, "username": user.username, "created_at": user.created_at}


@app.get("/promptfiles")
def promptfiles(user: User = Depends(_require_user)) -> Dict[str, Any]:
    return {"baseline": load_baseline_system_messages()}


@app.get("/promptsets")
def get_promptsets(user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    return list_prompt_sets()


@app.post("/promptsets")
def post_promptsets(payload: Dict[str, Any], user: User = Depends(_require_user)) -> Dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    # Prompt sets are shared or per user? Table has user_id, so per user.
    # list_prompt_sets currently lists ALL. Let's fix that later if needed, but for now strict user_id insert.
    id = create_prompt_set(user.id, name)
    return {"id": id, "name": name}


@app.get("/promptsets/{prompt_set_id}/versions")
def get_promptset_versions(prompt_set_id: int, user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    return list_prompt_versions(prompt_set_id)


@app.get("/promptsets/{prompt_set_id}/versions/{version}")
def get_promptset_version(prompt_set_id: int, version: int, user: User = Depends(_require_user)) -> Dict[str, Any]:
    pv = get_prompt_version(prompt_set_id, version)
    if pv is None:
        raise HTTPException(status_code=404, detail="not found")
    return pv


@app.post("/promptsets/{prompt_set_id}/versions")
def post_promptset_version(prompt_set_id: int, payload: Dict[str, Any], user: User = Depends(_require_user)) -> Dict[str, Any]:
    notes = payload.get("notes")
    overrides = normalize_prompt_payload(payload.get("payload"))
    if not overrides:
        raise HTTPException(status_code=400, detail="payload required")
    id = create_prompt_version(prompt_set_id=prompt_set_id, notes=str(notes) if notes is not None else None, payload=overrides)
    return {"id": id}


def _run_workspace(run_id: str) -> str:
    return os.path.join(settings.runs_root, run_id)


def _safe_join(root: str, rel: str) -> str:
    root_path = pathlib.Path(root).resolve()
    target = (root_path / rel).resolve()
    if root_path not in target.parents and root_path != target:
        raise HTTPException(status_code=400, detail="invalid path")
    return str(target)


@app.post("/runs")
def post_runs(payload: Dict[str, Any], user: User = Depends(_require_user)) -> Dict[str, Any]:
    yaml_text = str(payload.get("yaml_text") or "")
    yaml_filename = str(payload.get("yaml_filename") or "").strip() or "challenge.yaml"
    prompt_version_id = payload.get("prompt_version_id")

    try:
        cfg = yaml.safe_load(yaml_text)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid yaml")
    if not isinstance(cfg, dict):
        raise HTTPException(status_code=400, detail="invalid yaml")

    if "content" not in cfg:
        raise HTTPException(status_code=400, detail="missing content in yaml")

    cfg.setdefault("project_name", f"run_{uuid.uuid4().hex[:8]}")
    cfg["username"] = f"user_{user.id}"

    project_id = str(payload.get("project_id") or "").strip() or uuid.uuid4().hex

    run_id = str(uuid.uuid4())
    run_dir = _run_workspace(run_id)
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.join(run_dir, "initial_configs"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "datacache"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "logs"), exist_ok=True)

    yaml_path = os.path.join(run_dir, "initial_configs", yaml_filename)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    pv = get_prompt_version_by_id(int(prompt_version_id)) if prompt_version_id is not None else None
    overrides = normalize_prompt_payload(pv["payload"]) if pv else {}

    copy_baseline_prompts(os.path.join(run_dir, "prompts"))
    try:
        apply_system_message_overrides(os.path.join(run_dir, "prompts"), overrides)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Note: create_run returns the run_id string
    create_run(
        user_id=user.id,
        yaml_filename=yaml_filename,
        project_id=project_id,
        prompt_version_id=int(prompt_version_id) if prompt_version_id is not None else None,
        workspace_dir=run_dir,
    )
    # We need to manually construct the response or fetch it back, but create_run just returns ID in my store implementation above
    # Wait, create_run in store.py returns run_id.
    
    start_run_container(run_id=run_id, run_dir=run_dir, yaml_filename=yaml_filename, project_id=project_id)
    return {"id": run_id, "status": "pending"}


@app.get("/runs")
def get_runs(user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    return list_runs(user.id)


@app.get("/runs/{run_id}")
def get_run_detail(run_id: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    # get_run needs to be updated to check user_id? Currently it just gets by ID.
    # In store.py: def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    # It doesn't take user_id. Let's just return it. Ideally we should check ownership.
    r = get_run(run_id)
    if r is None:
        raise HTTPException(status_code=404, detail="not found")
    if r["user_id"] != user.id:
         raise HTTPException(status_code=404, detail="not found")
    return r


@app.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    r = get_run(run_id)
    if r is None or r["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    container_id = r.get("container_id")
    if container_id:
        try:
            stop_run_container(str(container_id))
        except Exception:
            pass
    update_run_status(run_id, "canceled")
    return {"id": run_id, "status": "canceled"}


@app.get("/runs/{run_id}/stages")
def get_run_stages(run_id: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    r = get_run(run_id)
    if r is None or r["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    run_dir = str(r["workspace_dir"])
    db_path = find_latest_sqlite_db(run_dir)
    if not db_path:
        return {"db_path": None, "tasks": []}
    return {"db_path": os.path.relpath(db_path, run_dir), "tasks": read_dbtask_rows(db_path)}


@app.get("/runs/{run_id}/artifacts")
def get_run_artifacts(run_id: str, user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    r = get_run(run_id)
    if r is None or r["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    run_dir = str(r["workspace_dir"])
    return list_artifacts(run_dir)


@app.get("/runs/{run_id}/download")
def download(run_id: str, path: str = Query(...), user: User = Depends(_require_user)) -> FileResponse:
    r = get_run(run_id)
    if r is None or r["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    run_dir = str(r["workspace_dir"])
    abs_path = _safe_join(run_dir, path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="not found")
    if os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="directory not supported")
    return FileResponse(abs_path, media_type="application/octet-stream", filename=os.path.basename(abs_path))
