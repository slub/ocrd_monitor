import functools
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def path_cache(fn: Callable[[Path], T]) -> Callable[[Path], T]:
    pathcache: dict[Path, tuple[T, float]] = {}

    def cache(path: Path) -> T:
        new_value = fn(path)
        pathcache[path] = new_value, path.stat().st_mtime
        return new_value

    @functools.wraps(fn)
    def wrapper(path: Path) -> T:
        if path not in pathcache:
            return cache(path)

        value, saved_timestamp = pathcache[path]
        last_modified = path.stat().st_mtime

        if last_modified > saved_timestamp:
            return cache(path)

        return value

    return wrapper
