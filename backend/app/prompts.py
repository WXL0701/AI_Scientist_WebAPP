from __future__ import annotations

import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

from .settings import settings


_SYSTEM_MESSAGE_RE = re.compile(
    r'("system_message"\s*:\s*f?""")(?P<body>[\s\S]*?)("""\s*,?\s*)',
    re.MULTILINE,
)



def get_prompts_dir() -> str:
    prompts_dir = os.path.join(settings.ai_scientist_root, "prompts")
    if os.path.isdir(prompts_dir):
        try:
            if any(f.startswith("system_") and f.endswith(".py") for f in os.listdir(prompts_dir)):
                return prompts_dir
        except OSError:
            pass

    docker_prompts_dir = "/app/prompts"
    if os.path.isdir(docker_prompts_dir):
        try:
            if any(f.startswith("system_") and f.endswith(".py") for f in os.listdir(docker_prompts_dir)):
                return docker_prompts_dir
        except OSError:
            pass

    return prompts_dir


def get_prompts_default_dir() -> str:
    return os.path.join(settings.ai_scientist_root, "AI_Scientist_WebAPP", "prompts_default")


def get_promptsets_root_dir() -> str:
    return os.path.join(settings.data_dir, "promptsets")


def get_promptset_dir(prompt_set_id: int) -> str:
    return os.path.join(get_promptsets_root_dir(), str(prompt_set_id))


def get_promptset_baseline_dir(prompt_set_id: int) -> str:
    return os.path.join(get_promptset_dir(prompt_set_id), "baseline_prompts")


def get_promptset_version_prompts_dir(prompt_set_id: int, version: int) -> str:
    return os.path.join(get_promptset_dir(prompt_set_id), "versions", str(version), "prompts")


def list_prompt_files_in_dir(prompts_dir: str) -> List[str]:
    if not os.path.isdir(prompts_dir):
        return []
    files: List[str] = []
    for name in os.listdir(prompts_dir):
        if name.startswith("system_") and name.endswith(".py"):
            files.append(name)
    files.sort()
    return files


def load_system_messages_from_dir(prompts_dir: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for filename in list_prompt_files_in_dir(prompts_dir):
        path = os.path.join(prompts_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        m = _SYSTEM_MESSAGE_RE.search(text)
        if m:
            result[filename] = m.group("body")
    return result


def copy_prompts_dir(src_dir: str, dst_dir: str) -> None:
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
    shutil.copytree(src_dir, dst_dir)

def _has_init_py(prompts_dir: str) -> bool:
    return os.path.isfile(os.path.join(prompts_dir, "__init__.py"))


def ensure_promptset_baseline(prompt_set_id: int) -> str:
    baseline_dir = get_promptset_baseline_dir(prompt_set_id)
    if list_prompt_files_in_dir(baseline_dir) and _has_init_py(baseline_dir):
        src_dir = get_prompts_dir()
        src_files = set(list_prompt_files_in_dir(src_dir))
        baseline_files = set(list_prompt_files_in_dir(baseline_dir))
        missing = src_files - baseline_files
        if missing:
            os.makedirs(baseline_dir, exist_ok=True)
            for filename in missing:
                shutil.copy2(os.path.join(src_dir, filename), os.path.join(baseline_dir, filename))
        return baseline_dir
    src_dir = get_prompts_dir()
    copy_prompts_dir(src_dir, baseline_dir)
    return baseline_dir


def materialize_promptset_version_prompts(prompt_set_id: int, version: int, overrides: Dict[str, str]) -> str:
    baseline_dir = ensure_promptset_baseline(prompt_set_id)
    version_dir = get_promptset_version_prompts_dir(prompt_set_id, version)
    copy_prompts_dir(baseline_dir, version_dir)
    apply_system_message_overrides(version_dir, overrides)
    return version_dir


def list_prompt_files() -> List[str]:
    prompts_dir = get_prompts_dir()
    if not os.path.exists(prompts_dir):
        return []
    files: List[str] = []
    for name in os.listdir(prompts_dir):
        if name.startswith("system_") and name.endswith(".py"):
            files.append(name)
    files.sort()
    return files


def load_baseline_system_messages() -> Dict[str, str]:
    prompts_dir = get_prompts_dir()
    result: Dict[str, str] = {}
    for filename in list_prompt_files():
        path = os.path.join(prompts_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        m = _SYSTEM_MESSAGE_RE.search(text)
        if m:
            result[filename] = m.group("body")
    return result


def copy_baseline_prompts(dst_dir: str) -> None:
    src_dir = get_prompts_dir()
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir)


def apply_system_message_overrides(prompts_dir: str, overrides: Dict[str, str]) -> List[Tuple[str, str]]:
    changed: List[Tuple[str, str]] = []
    for filename, new_body in overrides.items():
        if not filename.startswith("system_") or not filename.endswith(".py"):
            continue
        if '"""' in new_body:
            raise ValueError(f'prompt body contains triple quotes: {filename}')
        path = os.path.join(prompts_dir, filename)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        m = _SYSTEM_MESSAGE_RE.search(text)
        if not m:
            continue
        def _repl(mm: re.Match[str]) -> str:
            return f'{mm.group(1)}{new_body}{mm.group(3)}'

        new_text = _SYSTEM_MESSAGE_RE.sub(_repl, text, count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        changed.append((filename, "updated"))
    return changed


def normalize_prompt_payload(payload: Optional[Dict[str, str]]) -> Dict[str, str]:
    if not payload:
        return {}
    out: Dict[str, str] = {}
    for k, v in payload.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        out[k] = v
    return out
