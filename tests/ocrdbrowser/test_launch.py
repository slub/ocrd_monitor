from typing import cast

import pytest

import ocrdbrowser
from tests.ocrdbrowser.browserdoubles import BrowserSpy, BrowserTestDoubleFactory


@pytest.mark.asyncio
async def test__workspace__launch__spawns_new_ocrd_browser() -> None:
    owner = "the-owner"
    workspace = "path/to/workspace"
    process = await ocrdbrowser.launch(workspace, owner, BrowserTestDoubleFactory())

    process = cast(BrowserSpy, process)
    assert process.running is True
    assert process.owner() == owner
    assert process.workspace() == workspace


@pytest.mark.asyncio
async def test__workspace__launch_for_different_owners__both_processes_running() -> None:
    factory = BrowserTestDoubleFactory()

    first_process = await ocrdbrowser.launch("first-path", "first-owner", factory)
    second_process = await ocrdbrowser.launch(
        "second-path", "second-owner", factory, {first_process}
    )

    processes = {first_process, second_process}
    assert all(cast(BrowserSpy, process).running for process in processes)
    assert {p.owner() for p in processes} == {"first-owner", "second-owner"}
    assert {p.workspace() for p in processes} == {"first-path", "second-path"}


@pytest.mark.asyncio
async def test__workspace__launch_for_same_owner_and_workspace__does_not_start_new_process() -> (
    None
):
    owner = "the-owner"
    workspace = "the-workspace"
    factory = BrowserTestDoubleFactory()

    first_process = await ocrdbrowser.launch(workspace, owner, factory)
    second_process = await ocrdbrowser.launch(
        workspace, owner, factory, {first_process}
    )

    assert first_process is second_process
