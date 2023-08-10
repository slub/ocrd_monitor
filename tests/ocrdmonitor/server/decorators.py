import pytest
from tests import markers
from tests.decorators import compose

from tests.ocrdmonitor.server.fixtures.repository import (
    inmemory_repository,
    mongodb_repository,
)


use_custom_repository = compose(
    pytest.mark.asyncio,
    pytest.mark.parametrize(
        "repository",
        (
            pytest.param(inmemory_repository),
            pytest.param(
                mongodb_repository,
                marks=(pytest.mark.integration, markers.skip_if_no_docker),
            ),
        ),
    ),
)
