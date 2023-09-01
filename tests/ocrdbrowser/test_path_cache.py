from pathlib import Path
from typing import Iterator

import time
import pytest

from ocrdbrowser._cache import path_cache

TMPDIR = Path(__file__).parent / "tmpdir"
TMPFILE = TMPDIR / "tmp.txt"


@pytest.fixture(autouse=True)
def cleandir() -> Iterator[None]:
    TMPDIR.mkdir()

    yield

    TMPFILE.unlink(missing_ok=True)
    TMPDIR.rmdir()


def test__path_cache_decorator__returns_the_same_result_without_calling_func_again() -> (
    None
):
    call_count = 0

    @path_cache
    def fn(path: str | Path) -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    first = fn(TMPDIR)
    second = fn(TMPDIR)

    assert call_count == 1
    assert first == second


def test__when_cached_path_changes__calls_func_again() -> None:
    call_count = 0

    @path_cache
    def fn(path: str | Path) -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    fn(TMPDIR)

    time.sleep(1)

    TMPFILE.touch()

    fn(TMPDIR)

    assert call_count == 2
