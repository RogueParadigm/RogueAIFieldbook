from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def stable_seed(*parts: object, bits: int = 32, algorithm: str = "sha256") -> int:
    """Return the same unsigned seed on every Python process and machine."""
    if bits <= 0 or bits > 256 or bits % 8:
        raise ValueError("bits must be a positive multiple of 8 up to 256")
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    try:
        digest = hashlib.new(algorithm, payload).digest()
    except ValueError as error:
        raise ValueError(f"unsupported digest algorithm: {algorithm}") from error
    return int.from_bytes(digest[: bits // 8], "big")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path, base_dir: Path | None = None) -> str:
    """Keep provenance useful without leaking an external absolute directory."""
    resolved = path.resolve()
    base = (base_dir or Path.cwd()).resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        parent = resolved.parent.name or "root"
        return f"external/{parent}/{resolved.name}"


def write_metadata(path: Path, metadata: dict[str, Any]) -> Path:
    """Write the Fieldbook sidecar convention: artifact.ext.json."""
    sidecar = path.with_suffix(path.suffix + ".json")
    sidecar.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sidecar


def input_digests(paths: Iterable[Path], base_dir: Path | None = None) -> dict[str, str]:
    return {portable_path(path, base_dir): file_sha256(path) for path in paths}

