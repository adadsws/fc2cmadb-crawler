"""原地修改工具共用的本机批次历史，不删除或覆盖既有记录。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


HISTORY_ROOT = Path(__file__).resolve().parent.parent / "~outputs" / "undo-history"


def history_directory(tool_name: str) -> Path:
    return HISTORY_ROOT / tool_name


def write_batch(tool_name: str, entries: list[dict], root_path: Path | None = None) -> Path:
    directory = history_directory(tool_name)
    directory.mkdir(parents=True, exist_ok=True)
    batch_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid4().hex
    path = directory / f"{batch_id}.json"
    record = {"version": 1, "created_at": datetime.now().isoformat(), "entries": entries}
    if root_path is not None:
        record["root_path"] = str(root_path)
    with path.open("x", encoding="utf-8") as output:
        json.dump(record, output, ensure_ascii=False, indent=2)
    return path


def pending_batches(tool_name: str) -> list[Path]:
    directory = history_directory(tool_name)
    if not directory.is_dir():
        return []
    return [
        path for path in sorted(directory.glob("*.json"), reverse=True)
        if not path.with_suffix(".undone").exists()
    ]


def read_batch(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as source:
        record = json.load(source)
    if record.get("version") != 1 or not isinstance(record.get("entries"), list):
        raise ValueError(f"撤销记录格式无效: {path}")
    return record


def batch_folder_paths(record: dict, entry_path_key: str) -> list[str]:
    """优先展示处理入口路径；旧记录按受影响项目的父目录展示。"""
    root_path = record.get("root_path")
    if isinstance(root_path, str) and root_path:
        return [root_path]
    parents = {
        str(Path(entry[entry_path_key]).parent)
        for entry in record["entries"]
        if isinstance(entry, dict) and isinstance(entry.get(entry_path_key), str)
    }
    return sorted(parents, key=str.casefold)


def mark_undone(path: Path) -> None:
    marker = path.with_suffix(".undone")
    with marker.open("x", encoding="ascii") as output:
        output.write(datetime.now().isoformat())
