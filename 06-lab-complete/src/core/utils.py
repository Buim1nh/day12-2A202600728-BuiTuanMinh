from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any, Iterable


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(df, path: Path) -> None:
    ensure_parent(path)
    df.to_csv(path, index=False)


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def now_utc() -> datetime:
    return datetime.now(UTC)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return cleaned or "item"


def compact_join(items: Iterable[str], sep: str = ", ") -> str:
    return sep.join(item for item in items if item)


def first_sentence(text: str) -> str:
    chunks = re.split(r"(?<=[.!?])\s+", normalize_whitespace(text))
    return chunks[0] if chunks else normalize_whitespace(text)
