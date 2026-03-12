from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .settings import settings


ALLOWED_TEMPLATE_TYPES = (
    "hypothesis_summary",
    "experiment_reference",
    "experiment_template",
    "experiment_record_completion",
)

_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_TEMPLATE_BYTES = 512 * 1024


def get_templates_root_dir() -> str:
    return os.path.join(settings.ai_scientist_root, "templates")


def _validate_template_type(template_type: str) -> str:
    t = str(template_type or "").strip()
    if t not in ALLOWED_TEMPLATE_TYPES:
        raise ValueError("invalid template_type")
    return t


def _validate_template_name(template_name: str) -> str:
    n = str(template_name or "").strip()
    if not n or not _NAME_RE.fullmatch(n):
        raise ValueError("invalid template_name")
    return n


def _template_file_path(template_type: str, template_name: str) -> str:
    t = _validate_template_type(template_type)
    n = _validate_template_name(template_name)
    root = Path(get_templates_root_dir()).resolve()
    target = (root / t / f"{n}.md").resolve()
    if root not in target.parents:
        raise ValueError("invalid path")
    return str(target)


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_templates(template_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    root = Path(get_templates_root_dir())
    if template_type is not None:
        types = [_validate_template_type(template_type)]
    else:
        types = list(ALLOWED_TEMPLATE_TYPES)

    output: Dict[str, List[Dict[str, Any]]] = {}
    for t in types:
        type_dir = root / t
        items: List[Dict[str, Any]] = []
        if type_dir.is_dir():
            for f in type_dir.glob("*.md"):
                try:
                    stat = f.stat()
                except OSError:
                    continue
                items.append(
                    {
                        "name": f.stem,
                        "filename": f.name,
                        "size": int(stat.st_size),
                        "updated_at": _iso_utc(stat.st_mtime),
                        "is_default": f.stem == "default",
                    }
                )
        items.sort(key=lambda x: (0 if x["is_default"] else 1, x["name"]))
        output[t] = items
    return output


def read_template(template_type: str, template_name: str) -> str:
    path = _template_file_path(template_type, template_name)
    if not os.path.isfile(path):
        raise FileNotFoundError("template not found")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_template(template_type: str, template_name: str, content: str) -> Dict[str, Any]:
    if not isinstance(content, str):
        raise ValueError("invalid content")
    data = content.encode("utf-8")
    if len(data) > _MAX_TEMPLATE_BYTES:
        raise ValueError("template too large")
    path = _template_file_path(template_type, template_name)
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    stat = os.stat(path)
    return {
        "name": template_name,
        "template_type": template_type,
        "size": int(stat.st_size),
        "updated_at": _iso_utc(stat.st_mtime),
    }


def delete_template(template_type: str, template_name: str) -> None:
    if template_name == "default":
        raise ValueError("default template cannot be deleted")
    path = _template_file_path(template_type, template_name)
    if not os.path.isfile(path):
        raise FileNotFoundError("template not found")
    os.remove(path)


def parse_template_name_from_filename(filename: str) -> str:
    base = os.path.basename(str(filename or "").strip())
    if not base.lower().endswith(".md"):
        raise ValueError("only .md files are supported")
    stem = base[:-3]
    return _validate_template_name(stem)


def validate_template_checks() -> Dict[str, Any]:
    templates = list_templates()
    ref_names = {x["name"] for x in templates.get("experiment_reference", []) if x["name"] != "default"}
    exp_names = {x["name"] for x in templates.get("experiment_template", []) if x["name"] != "default"}

    missing_template_pairs = sorted(list(ref_names - exp_names))
    missing_reference_pairs = sorted(list(exp_names - ref_names))

    applicability_checks: List[Dict[str, Any]] = []
    for name in sorted(ref_names):
        try:
            content = read_template("experiment_reference", name)
        except FileNotFoundError:
            applicability_checks.append({"name": name, "ok": False, "reason": "模板不存在"})
            continue
        has_app = any(
            line.strip().startswith("# 0.") and "适用性描述" in line
            for line in content.splitlines()
        )
        applicability_checks.append(
            {
                "name": name,
                "ok": has_app,
                "reason": "" if has_app else "缺少 # 0. 适用性描述 段落",
            }
        )

    return {
        "missing_template_pairs": missing_template_pairs,
        "missing_reference_pairs": missing_reference_pairs,
        "reference_applicability": applicability_checks,
    }
