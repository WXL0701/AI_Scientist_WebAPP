from __future__ import annotations

import os
import pathlib
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import yaml
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse

from .ai_outputs import (
    find_latest_sqlite_db,
    list_artifacts,
    read_dbtask_rows,
    resolve_container_result_path,
)
from .prompts import (
    apply_system_message_overrides,
    copy_prompts_dir,
    copy_baseline_prompts,
    ensure_promptset_baseline,
    get_prompts_default_dir,
    get_promptset_dir,
    get_promptset_version_prompts_dir,
    list_prompt_files_in_dir,
    load_baseline_system_messages,
    load_system_messages_from_dir,
    materialize_promptset_version_prompts,
    normalize_prompt_payload,
)
from .runner import start_run_container, stop_run_container
from .security import create_access_token, decode_token, hash_password, new_salt, verify_password
from .settings import settings
from .template_files import (
    delete_template,
    list_templates,
    parse_template_name_from_filename,
    read_template,
    validate_template_checks,
    write_template,
)
from .store import (
    User,
    create_prompt_set,
    create_prompt_version,
    create_run,
    create_user,
    get_prompt_set,
    get_prompt_version,
    get_prompt_version_by_id,
    get_user_by_username,
    get_user_by_id,
    get_run,
    get_latest_run_by_project,
    init_db,
    list_prompt_sets,
    list_prompt_sets_all,
    list_prompt_versions,
    list_runs,
    list_runs_all,
    list_users,
    get_run_status_counts,
    get_run_daily_counts,
    set_user_role,
    update_run_status,
    delete_run,
    delete_prompt_set,
    delete_prompt_version,
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


def _require_admin(user: User = Depends(_require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
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
        create_user("Admin", pw_hash, salt, role="admin")
    else:
        admin, _pw_hash, _salt = admin_user
        if admin.role != "admin":
            set_user_role(admin.id, "admin")


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
    user = create_user(username, pw_hash, salt, role="user")
    token = create_access_token(user.id, user.username, user.role)
    return {
        "access_token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


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
    token = create_access_token(user.id, user.username, user.role)
    return {
        "access_token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


@app.get("/me")
def me(user: User = Depends(_require_user)) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at,
    }


@app.get("/admin/users")
def admin_list_users(_user: User = Depends(_require_admin)) -> List[Dict[str, Any]]:
    return list_users()


@app.post("/admin/users")
def admin_create_user(payload: Dict[str, Any], _user: User = Depends(_require_admin)) -> Dict[str, Any]:
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    role = str(payload.get("role") or "user").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="username/password required")
    if not username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="username must be alphanumeric (can include _ -)")
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="invalid role")
    existing = get_user_by_username(username)
    if existing is not None:
        raise HTTPException(status_code=409, detail="username exists")
    salt = new_salt()
    pw_hash = hash_password(password, salt)
    user = create_user(username, pw_hash, salt, role=role)
    return {"id": user.id, "username": user.username, "role": user.role, "created_at": user.created_at}


@app.get("/stats/dashboard")
def dashboard_stats(user: User = Depends(_require_user)) -> Dict[str, Any]:
    status_counts = get_run_status_counts(user.id)
    total = sum(status_counts.values())
    running = status_counts.get("running", 0) + status_counts.get("pending", 0)
    succeeded = status_counts.get("completed", 0)
    failed = status_counts.get("failed", 0)

    today = datetime.utcnow().date()
    start_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    daily_counts = get_run_daily_counts(user.id, start_date)
    daily_map = {d: c for d, c in daily_counts}
    recent_activity = []
    for i in range(7):
        day = (today - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        recent_activity.append({"date": day, "count": daily_map.get(day, 0)})

    distribution = []
    for status, count in status_counts.items():
        distribution.append({"status": status, "count": count})

    return {
        "summary": {
            "total": total,
            "running": running,
            "succeeded": succeeded,
            "failed": failed,
        },
        "recent_activity": recent_activity,
        "status_distribution": distribution,
    }


@app.get("/promptfiles")
def promptfiles(user: User = Depends(_require_user)) -> Dict[str, Any]:
    return {"baseline": load_baseline_system_messages()}


@app.get("/promptsets/{prompt_set_id}/promptfiles")
def promptset_promptfiles(prompt_set_id: int, user: User = Depends(_require_user)) -> Dict[str, Any]:
    ps = get_prompt_set(prompt_set_id)
    if ps is None or (ps["user_id"] != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="not found")
    baseline_dir = ensure_promptset_baseline(prompt_set_id)
    return {"baseline": load_system_messages_from_dir(baseline_dir)}


@app.get("/promptsets")
def get_promptsets(user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    if user.role == "admin":
        return list_prompt_sets_all()
    return list_prompt_sets(user.id)


@app.post("/promptsets")
def post_promptsets(payload: Dict[str, Any], user: User = Depends(_require_user)) -> Dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    # Prompt sets are shared or per user? Table has user_id, so per user.
    # list_prompt_sets currently lists ALL. Let's fix that later if needed, but for now strict user_id insert.
    id = create_prompt_set(user.id, name)
    try:
        baseline_dir = ensure_promptset_baseline(id)
        baseline_payload = load_system_messages_from_dir(baseline_dir)
        pv_id, version = create_prompt_version(
            prompt_set_id=id,
            notes="baseline",
            payload=baseline_payload,
        )
        materialize_promptset_version_prompts(id, version, baseline_payload)
    except Exception:
        raise HTTPException(status_code=500, detail="failed to initialize prompt baseline")
    return {"id": id, "name": name}


@app.delete("/promptsets/{prompt_set_id}")
def delete_promptset(prompt_set_id: int, user: User = Depends(_require_user)) -> Dict[str, Any]:
    ps = get_prompt_set(prompt_set_id)
    if ps is None or ps["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    try:
        root_dir = get_promptset_dir(prompt_set_id)
        if os.path.isdir(root_dir):
            shutil.rmtree(root_dir)
    except Exception:
        pass
    delete_prompt_set(prompt_set_id)
    return {"id": prompt_set_id, "status": "deleted"}


@app.delete("/promptsets/{prompt_set_id}/versions/{version}")
def delete_promptset_version(prompt_set_id: int, version: int, user: User = Depends(_require_user)) -> Dict[str, Any]:
    ps = get_prompt_set(prompt_set_id)
    if ps is None or ps["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    pv = get_prompt_version(prompt_set_id, version)
    if pv is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        version_root = os.path.join(get_promptset_dir(prompt_set_id), "versions", str(version))
        if os.path.isdir(version_root):
            shutil.rmtree(version_root)
    except Exception:
        pass
    delete_prompt_version(prompt_set_id, version)
    return {"prompt_set_id": prompt_set_id, "version": version, "status": "deleted"}

@app.get("/promptsets/{prompt_set_id}/versions")
def get_promptset_versions(prompt_set_id: int, user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    ps = get_prompt_set(prompt_set_id)
    if ps is None or (ps["user_id"] != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="not found")
    return list_prompt_versions(prompt_set_id)


@app.get("/promptsets/{prompt_set_id}/versions/{version}")
def get_promptset_version(prompt_set_id: int, version: int, user: User = Depends(_require_user)) -> Dict[str, Any]:
    ps = get_prompt_set(prompt_set_id)
    if ps is None or (ps["user_id"] != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="not found")
    pv = get_prompt_version(prompt_set_id, version)
    if pv is None:
        raise HTTPException(status_code=404, detail="not found")
    return pv


@app.get("/promptsets/{prompt_set_id}/versions/{version}/promptfiles")
def get_promptset_version_promptfiles(prompt_set_id: int, version: int, user: User = Depends(_require_user)) -> Dict[str, Any]:
    ps = get_prompt_set(prompt_set_id)
    if ps is None or (ps["user_id"] != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="not found")
    pv = get_prompt_version(prompt_set_id, version)
    if pv is None:
        raise HTTPException(status_code=404, detail="not found")
    version_dir = get_promptset_version_prompts_dir(prompt_set_id, version)
    has_prompts = list_prompt_files_in_dir(version_dir)
    has_init = os.path.isfile(os.path.join(version_dir, "__init__.py"))
    if not has_prompts or not has_init:
        overrides = normalize_prompt_payload(pv.get("payload"))
        materialize_promptset_version_prompts(prompt_set_id, version, overrides)
    return {"prompts": load_system_messages_from_dir(version_dir)}


@app.post("/promptsets/{prompt_set_id}/versions")
def post_promptset_version(prompt_set_id: int, payload: Dict[str, Any], user: User = Depends(_require_user)) -> Dict[str, Any]:
    ps = get_prompt_set(prompt_set_id)
    if ps is None or ps["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    notes = payload.get("notes")
    overrides = normalize_prompt_payload(payload.get("payload"))
    for v in overrides.values():
        if '"""' in v:
            raise HTTPException(status_code=400, detail="prompt body contains triple quotes")
    pv_id, version = create_prompt_version(prompt_set_id=prompt_set_id, notes=str(notes) if notes is not None else None, payload=overrides)
    try:
        materialize_promptset_version_prompts(prompt_set_id, version, overrides)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="failed to materialize prompt version")
    return {"id": pv_id, "version": version}


@app.get("/templates")
def get_templates(template_type: Optional[str] = Query(default=None), user: User = Depends(_require_user)) -> Dict[str, Any]:
    try:
        data = list_templates(template_type=template_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if template_type is not None:
        return {"template_type": template_type, "items": data.get(template_type, [])}
    return {"templates": data}


@app.get("/templates/checks")
def get_template_checks(user: User = Depends(_require_user)) -> Dict[str, Any]:
    return validate_template_checks()


@app.get("/templates/{template_type}/{template_name}")
def get_template_content(template_type: str, template_name: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    try:
        content = read_template(template_type=template_type, template_name=template_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="not found")
    return {"template_type": template_type, "name": template_name, "content": content}


@app.post("/templates/upload")
def upload_template(
    template_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(_require_user),
) -> Dict[str, Any]:
    try:
        template_name = parse_template_name_from_filename(file.filename or "")
        data = file.file.read()
        content = data.decode("utf-8")
        info = write_template(template_type=template_type, template_name=template_name, content=content)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="file must be utf-8")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return info


@app.put("/templates/{template_type}/{template_name}")
def update_template_content(
    template_type: str,
    template_name: str,
    payload: Dict[str, Any],
    user: User = Depends(_require_user),
) -> Dict[str, Any]:
    content = payload.get("content")
    try:
        info = write_template(template_type=template_type, template_name=template_name, content=content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return info


@app.delete("/templates/{template_type}/{template_name}")
def remove_template(template_type: str, template_name: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    try:
        delete_template(template_type=template_type, template_name=template_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="not found")
    return {"template_type": template_type, "name": template_name, "status": "deleted"}


def _run_workspace(user_id: int, run_id: str) -> str:
    return os.path.join(settings.runs_root, f"user_{user_id}", run_id)


def _safe_join(root: str, rel: str) -> str:
    root_path = pathlib.Path(root).resolve()
    target = (root_path / rel).resolve()
    if root_path not in target.parents and root_path != target:
        raise HTTPException(status_code=400, detail="invalid path")
    return str(target)


@app.post("/runs")
def post_runs(payload: Dict[str, Any], user: User = Depends(_require_user)) -> Dict[str, Any]:
    yaml_filename = str(payload.get("yaml_filename") or "").strip() or "challenge.yaml"
    prompt_version_id = payload.get("prompt_version_id")

    yaml_text = str(payload.get("yaml_text") or "").strip()
    if yaml_text:
        try:
            cfg = yaml.safe_load(yaml_text)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid yaml")
        if not isinstance(cfg, dict):
            raise HTTPException(status_code=400, detail="invalid yaml")
    else:
        content = str(payload.get("content") or "")
        if not content.strip():
            raise HTTPException(status_code=400, detail="missing content in payload")
        project_name = str(payload.get("project_name") or "").strip()
        cfg = {
            "project_name": project_name or f"run_{uuid.uuid4().hex[:8]}",
            "username": f"user_{user.id}",
            "max_workers": 1,
            "content": content,
        }

    if "content" not in cfg:
        raise HTTPException(status_code=400, detail="missing content in yaml")

    cfg.setdefault("project_name", f"run_{uuid.uuid4().hex[:8]}")
    cfg["username"] = f"user_{user.id}"

    project_id = str(payload.get("project_id") or "").strip() or uuid.uuid4().hex

    run_id = str(uuid.uuid4())
    run_dir = _run_workspace(user.id, run_id)
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.join(run_dir, "initial_configs"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "datacache"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "logs"), exist_ok=True)

    yaml_path = os.path.join(run_dir, "initial_configs", yaml_filename)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    username_dir = f"user_{user.id}"
    precreate_dirs = [
        os.path.join(run_dir, "datacache", username_dir, "propose"),
        os.path.join(run_dir, "datacache", username_dir, "scripts"),
        os.path.join(run_dir, "datacache", username_dir, "code"),
        os.path.join(run_dir, "datacache", username_dir, "experiment"),
        os.path.join(run_dir, "datacache", username_dir, "subtask"),
        os.path.join(run_dir, "datacache", username_dir, "defense"),
        os.path.join(run_dir, "datacache", username_dir, "design"),
        os.path.join(run_dir, "datacache", username_dir, "challenge"),
    ]
    for d in precreate_dirs:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass

    pv = get_prompt_version_by_id(int(prompt_version_id)) if prompt_version_id is not None else None
    if prompt_version_id is not None and pv is None:
        raise HTTPException(status_code=404, detail="not found")
    if pv is not None:
        ps = get_prompt_set(int(pv["prompt_set_id"]))
        if ps is None or ps["user_id"] != user.id:
            raise HTTPException(status_code=404, detail="not found")
    overrides = normalize_prompt_payload(pv["payload"]) if pv else {}

    run_prompts_dir = os.path.join(run_dir, "prompts")
    def _has_init_py(prompts_dir: str) -> bool:
        return os.path.isfile(os.path.join(prompts_dir, "__init__.py"))
    if pv:
        prompt_set_id = int(pv["prompt_set_id"])
        prompt_set_version = int(pv["version"])
        src_version_dir = get_promptset_version_prompts_dir(prompt_set_id, prompt_set_version)
        if list_prompt_files_in_dir(src_version_dir) and _has_init_py(src_version_dir):
            copy_prompts_dir(src_version_dir, run_prompts_dir)
        else:
            try:
                materialize_promptset_version_prompts(prompt_set_id, prompt_set_version, overrides)
                copy_prompts_dir(src_version_dir, run_prompts_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception:
                raise HTTPException(status_code=500, detail="failed to prepare prompts for run")
    else:
        copy_baseline_prompts(run_prompts_dir)

    # Note: create_run returns the run_id string
    create_run(
        user_id=user.id,
        yaml_filename=yaml_filename,
        project_id=project_id,
        project_name=project_name if project_name else None,
        prompt_version_id=int(prompt_version_id) if prompt_version_id is not None else None,
        workspace_dir=run_dir,
        run_id=run_id,
    )
    
    start_run_container(run_id=run_id, run_dir=run_dir, yaml_filename=yaml_filename, project_id=project_id)
    return {"id": run_id, "status": "pending"}


@app.delete("/runs/{run_id}")
def delete_run_endpoint(run_id: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    r = get_run(run_id)
    if r is None or r["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not found")
    
    # Try to stop container if running
    if r["status"] in ("running", "pending"):
        container_id = r.get("container_id")
        if container_id:
            try:
                stop_run_container(str(container_id))
            except Exception:
                pass

    # Remove workspace dir
    run_dir = str(r["workspace_dir"])
    if os.path.exists(run_dir):
        # Safety check: run_dir must be inside runs_root
        try:
            root_path = pathlib.Path(settings.runs_root).resolve()
            target_path = pathlib.Path(run_dir).resolve()
            if root_path in target_path.parents:
                shutil.rmtree(run_dir)
        except Exception:
            pass

    delete_run(run_id)
    return {"id": run_id, "status": "deleted"}


@app.get("/runs")
def get_runs(user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    if user.role == "admin":
        return list_runs_all()
    return list_runs(user.id)


@app.get("/runs/{run_id}")
def get_run_detail(run_id: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    # get_run needs to be updated to check user_id? Currently it just gets by ID.
    # In store.py: def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    # It doesn't take user_id. Let's just return it. Ideally we should check ownership.
    r = get_run(run_id)
    if r is None:
        raise HTTPException(status_code=404, detail="not found")
    if r["user_id"] != user.id and user.role != "admin":
         raise HTTPException(status_code=404, detail="not found")
    return r


@app.get("/runs/by_project/{project_id}")
def get_run_by_project(project_id: str, user: User = Depends(_require_user)) -> Dict[str, Any]:
    r = get_latest_run_by_project(user.id, project_id)
    if r is None:
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
    if r is None or (r["user_id"] != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="not found")
    run_dir = str(r["workspace_dir"])
    db_path = find_latest_sqlite_db(run_dir)
    if not db_path:
        return {"db_path": None, "tasks": []}
    tasks = read_dbtask_rows(db_path)
    for t in tasks:
        rp = t.get("result_path")
        if not rp:
            continue
        resolved = resolve_container_result_path(run_dir, str(rp))
        if resolved and os.path.exists(resolved):
            t["download_path"] = os.path.relpath(resolved, run_dir)
    return {"db_path": os.path.relpath(db_path, run_dir), "tasks": tasks}


@app.get("/runs/{run_id}/artifacts")
def get_run_artifacts(run_id: str, user: User = Depends(_require_user)) -> List[Dict[str, Any]]:
    r = get_run(run_id)
    if r is None or (r["user_id"] != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="not found")
    run_dir = str(r["workspace_dir"])
    return list_artifacts(run_dir)


@app.get("/runs/{run_id}/download")
def download(run_id: str, path: str = Query(...), user: User = Depends(_require_user)) -> FileResponse:
    r = get_run(run_id)
    if r is None or (r["user_id"] != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="not found")
    run_dir = str(r["workspace_dir"])
    abs_path = _safe_join(run_dir, path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="not found")
    if os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="directory not supported")
    return FileResponse(abs_path, media_type="application/octet-stream", filename=os.path.basename(abs_path))
