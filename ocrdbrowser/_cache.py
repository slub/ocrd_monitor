from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def path_cache(fn: Callable[[Path], T]) -> Callable[[Path], T]:
    pathcache: dict[Path, tuple[T, float]] = {}

    def cache(path: Path) -> T:
        new_value = fn(path)
        pathcache[path] = new_value, path.stat().st_mtime
        return new_value

    def wrapper(path: Path) -> T:
        if path not in pathcache:
            return cache(path)

        value, saved_timestamp = pathcache[path]
        saved_datetime = datetime.fromtimestamp(saved_timestamp)
        last_modified = datetime.fromtimestamp(path.stat().st_mtime)

        if last_modified > saved_datetime:
            return cache(path)

        return value

    return wrapper
