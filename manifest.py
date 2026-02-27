from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Literal

StoredAs = Literal["raw", "gzip"]


@dataclass
class ChunkEntry:
    index: int
    filename: str          
    stored_as: StoredAs      # raw|gzip
    size_raw: int
    size_stored: int
    sha256_raw: str
    sha256_stored: str


@dataclass
class Manifest:
    version: int
    original_filename: str
    chunk_size: int
    compression_level: int
    min_gain_ratio: float
    created_at_unix: int
    chunks: list[ChunkEntry]
    sha256_file_raw: str
    size_file_raw: int
    size_file_stored_total: int

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["chunks"] = [asdict(c) for c in self.chunks]
        return d


def write_manifest(folder: str | Path, manifest: Manifest) -> Path:
    folder = Path(folder)
    path = folder / "manifest.json"
    path.write_text(_json_dumps(manifest.to_dict()), encoding="utf-8")
    return path


def read_manifest(folder: str | Path) -> Manifest:
    folder = Path(folder)
    path = folder / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"manifest.json não encontrado em: {folder}")

    data = _json_loads(path.read_text(encoding="utf-8"))
    chunks = [ChunkEntry(**c) for c in data["chunks"]]
    return Manifest(
        version=data["version"],
        original_filename=data["original_filename"],
        chunk_size=data["chunk_size"],
        compression_level=data["compression_level"],
        min_gain_ratio=data["min_gain_ratio"],
        created_at_unix=data["created_at_unix"],
        chunks=chunks,
        sha256_file_raw=data["sha256_file_raw"],
        size_file_raw=data["size_file_raw"],
        size_file_stored_total=data["size_file_stored_total"],
    )


def _json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _json_loads(s: str) -> Any:
    import json
    return json.loads(s)
