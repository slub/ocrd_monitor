import pytest
from tests.decorators import compose

from tests.ocrdmonitor.server.fixtures.repository import (
    inmemory_repository,
    mongodb_repository,
)


use_custom_repository = compose(
    pytest.mark.asyncio,
    pytest.mark.no_auto_repository,
    pytest.mark.parametrize(
        "repository",
        (
            pytest.param(inmemory_repository),
            pytest.param(
                mongodb_repository,
                marks=(pytest.mark.integration, pytest.mark.needs_docker),
            ),
        ),
    ),
)
