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


def list_prompt_files() -> List[str]:
    prompts_dir = os.path.join(settings.ai_scientist_root, "prompts")
    files: List[str] = []
    for name in os.listdir(prompts_dir):
        if name.startswith("system_") and name.endswith(".py"):
            files.append(name)
    files.sort()
    return files


def load_baseline_system_messages() -> Dict[str, str]:
    prompts_dir = os.path.join(settings.ai_scientist_root, "prompts")
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
    src_dir = os.path.join(settings.ai_scientist_root, "prompts")
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
