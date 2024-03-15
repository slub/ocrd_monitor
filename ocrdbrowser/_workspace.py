from __future__ import annotations

from pathlib import Path
from typing import List

from ._cache import path_cache


def is_valid(workspace: str) -> bool:
    return (Path(workspace) / "mets.xml").exists()


# no way to update: @path_cache
def list_all(path: Path) -> List[str]:
    # recursively enumerate METS file paths (excluding .backup subdirs)
    return [
        str(workspace.parent)
        for workspace in path.rglob("mets.xml")
        if not workspace.match(".backup/*/mets.xml")
    ]
