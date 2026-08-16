from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write_text(self, visibility: str, relative: str, content: str) -> Path:
        path = self._path(visibility, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def write_bytes(self, visibility: str, relative: str, content: bytes) -> Path:
        path = self._path(visibility, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def adopt(self, visibility: str, relative: str, source: Path) -> Path:
        path = self._path(visibility, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, path)
        return path

    def paths(self, visibility: str) -> list[str]:
        root = self.root / visibility
        if not root.exists():
            return []
        return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())

    def _path(self, visibility: str, relative: str) -> Path:
        if visibility not in {"public", "private"}:
            raise ValueError(f"invalid artifact visibility: {visibility}")
        relative_path = PurePosixPath(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts or not relative_path.parts:
            raise ValueError(f"invalid artifact path: {relative}")
        return self.root / visibility / Path(*relative_path.parts)
