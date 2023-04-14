from pathlib import Path
import pytest
from typing import Any, Awaitable, Callable, TypeVar

from testcontainers.general import DockerContainer

from ocrdmonitor.processstatus import ProcessState
from ocrdmonitor.sshremote import SSHRemote
from tests.ocrdmonitor.sshcontainer import (
    get_process_group_from_container,
    SSHConfig,
    KEYDIR,
)

T = TypeVar("T")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ps_over_ssh__returns_list_of_process_status(
    openssh_server: DockerContainer,
) -> None:
    process_group = get_process_group_from_container(openssh_server)
    sut = SSHRemote(
        config=SSHConfig(
            host="localhost",
            port=2222,
            user="testcontainer",
            keyfile=Path(KEYDIR) / "id.rsa",
        ),
    )

    actual = await run_until_truthy(sut.process_status, process_group)

    first_process = actual[0]
    assert first_process.pid == process_group
    assert first_process.state == ProcessState.SLEEPING


async def run_until_truthy(fn: Callable[..., Awaitable[T]], *args: Any) -> T:
    while not (result := await fn(*args)):
        continue

    return result
