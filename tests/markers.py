import shutil

import pytest


def browse_ocrd_not_available() -> bool:
    browse_ocrd = shutil.which("browse-ocrd")
    broadway = shutil.which("broadwayd")
    return not all((browse_ocrd, broadway))


def docker_not_available() -> bool:
    return not bool(shutil.which("docker"))


skip_if_no_docker = pytest.mark.skipif(
    docker_not_available(),
    reason="Skipping because Docker is not available",
)

skip_if_no_browse_ocrd = pytest.mark.skipif(
    browse_ocrd_not_available(),
    reason="Skipping because browse-ocrd or broadwayd are not available",
)
