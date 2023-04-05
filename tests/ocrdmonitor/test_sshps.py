from pathlib import Path
from typing import Any, Callable, TypeVar

import pytest
from testcontainers.general import DockerContainer

from ocrdmonitor.processstatus import ProcessState
from ocrdmonitor.sshps import process_status
from tests.ocrdmonitor.sshcontainer import (
    get_process_group_from_container,
    SSHConfig,
    KEYDIR,
)

T = TypeVar("T")


def run_until_truthy(fn: Callable[..., T], *args: Any) -> T:
    while not (result := fn(*args)):
        continue

    return result


@pytest.mark.integration
def test_ps_over_ssh__returns_list_of_process_status(
    openssh_server: DockerContainer,
) -> None:
    process_group = get_process_group_from_container(openssh_server)

    config = SSHConfig(
        host="localhost",
        port=2222,
        user="testcontainer",
        keyfile=Path(KEYDIR) / "id.rsa",
    )

    actual = run_until_truthy(process_status, config, process_group)

    first_process = actual[0]
    assert first_process.pid == process_group
    assert first_process.state == ProcessState.SLEEPING
