from __future__ import annotations

import os
import threading
from typing import Optional

import docker

from .settings import settings
from .store import update_run_status


def _write_container_logs(container: docker.models.containers.Container, stdout_path: str) -> None:
    os.makedirs(os.path.dirname(stdout_path), exist_ok=True)
    with open(stdout_path, "ab") as f:
        for chunk in container.logs(stream=True, follow=True):
            if not chunk:
                continue
            f.write(chunk)
            f.flush()


def start_run_container(run_id: str, run_dir: str, yaml_filename: str, project_id: str) -> str:
    client = docker.from_env()

    host_root = settings.ai_scientist_root
    host_venv = os.path.join(settings.ai_scientist_root, ".venv")
    host_initial = os.path.join(run_dir, "initial_configs")
    host_datacache = os.path.join(run_dir, "datacache")
    host_prompts = os.path.join(run_dir, "prompts")
    host_logs = os.path.join(run_dir, "logs")

    os.makedirs(host_initial, exist_ok=True)
    os.makedirs(host_datacache, exist_ok=True)
    os.makedirs(host_prompts, exist_ok=True)
    os.makedirs(host_logs, exist_ok=True)

    passthrough_keys = [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "OPENAI_ORG_ID",
        "ANTHROPIC_API_KEY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
    ]
    env = {
        "YAML_FILENAME": yaml_filename,
        "PROJECT_ID": project_id,
    }
    for k in passthrough_keys:
        v = os.getenv(k)
        if v:
            env[k] = v

    extra_mounts = {}
    host_python_link = os.path.join(host_venv, "bin", "python")
    resolved_python = os.path.realpath(host_python_link)
    for prefix in ["/root/miniconda3", "/opt/conda"]:
        if resolved_python.startswith(prefix) and os.path.exists(prefix):
            extra_mounts[prefix] = {"bind": prefix, "mode": "ro"}

    volumes = {
        host_root: {"bind": "/home/guv/AI_Scientist", "mode": "ro"},
        host_venv: {"bind": "/home/guv/AI_Scientist/.venv", "mode": "ro"},
        host_initial: {"bind": "/home/guv/AI_Scientist/initial_configs", "mode": "rw"},
        host_datacache: {"bind": "/home/guv/AI_Scientist/agent-service/datacache", "mode": "rw"},
        host_prompts: {"bind": "/home/guv/AI_Scientist/prompts", "mode": "rw"},
        host_logs: {"bind": "/logs", "mode": "rw"},
    }
    volumes.update(extra_mounts)

    container = client.containers.run(
        image=settings.runner_image,
        detach=True,
        environment=env,
        volumes=volumes,
    )

    update_run_status(run_id, "running", container_id=container.id)

    def _bg() -> None:
        try:
            _write_container_logs(container, os.path.join(host_logs, "stdout.log"))
        except Exception:
            pass

    t = threading.Thread(target=_bg, daemon=True)
    t.start()

    def _waiter() -> None:
        try:
            res = container.wait()
            exit_code = int(res.get("StatusCode", 1))
            update_run_status(run_id, "completed" if exit_code == 0 else "failed", exit_code=exit_code)
        except Exception:
            update_run_status(run_id, "failed")

    w = threading.Thread(target=_waiter, daemon=True)
    w.start()

    return container.id


def stop_run_container(container_id: str) -> None:
    client = docker.from_env()
    container = client.containers.get(container_id)
    container.stop(timeout=3)
