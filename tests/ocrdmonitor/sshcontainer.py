import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Self, Type

import pytest
from testcontainers.general import DockerContainer

KEYDIR = Path("tests/ocrdmonitor/server/keys")

PS = "ps -o pid --no-headers"


@dataclass
class SSHConfig:
    host: str
    port: int
    user: str
    keyfile: Path


@dataclass
class KeyPair:
    private: Path
    public: Path

    @classmethod
    def generate(cls: Type[Self], name: str = "id.rsa") -> Self:
        KEYDIR.mkdir(parents=True, exist_ok=True)
        private_key_path = KEYDIR / name
        public_key_path = KEYDIR / f"{name}.pub"
        subprocess.run(
            f"ssh-keygen -t rsa -P '' -f {private_key_path.as_posix()}",
            shell=True,
            check=True,
        )

        return cls(private_key_path, public_key_path)

    def unlink(self) -> None:
        self.private.unlink(missing_ok=True)
        self.public.unlink(missing_ok=True)


def ensure_known_hosts_in_ci() -> None:
    if not os.getenv("GITHUB_ACTIONS"):
        return

    known_hosts = Path("~/.ssh/known_hosts")
    known_hosts.parent.mkdir(parents=True, exist_ok=True)
    known_hosts.touch(exist_ok=True)


def remove_existing_host_key() -> None:
    subprocess.run("ssh-keygen -R [localhost]:2222", shell=True, check=True)


def configure_container(pub_key: Path) -> DockerContainer:
    return (
        DockerContainer(image="lscr.io/linuxserver/openssh-server:latest")
        .with_bind_ports(2222, 2222)
        .with_env("PUBLIC_KEY", pub_key.read_text())
        .with_env("USER_NAME", "testcontainer")
    )


def get_process_group_from_container(container: DockerContainer) -> int:
    result = container.exec(PS)
    return int(result.output.splitlines()[0].strip())


@pytest.fixture
def ssh_keys() -> Iterator[KeyPair]:
    ensure_known_hosts_in_ci()
    keypair = KeyPair.generate()

    yield keypair

    keypair.unlink()


@pytest.fixture
def openssh_server(ssh_keys: KeyPair) -> Iterator[DockerContainer]:
    remove_existing_host_key()
    keypair = ssh_keys
    with configure_container(keypair.public) as container:
        time.sleep(1)  # wait for ssh server to start
        yield container

    remove_existing_host_key()
