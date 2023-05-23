from typing import Any, Awaitable, Callable, Coroutine, ParamSpec
import pytest

from tests.ocrdmonitor.server.fixtures.repository import (
    inmemory_repository,
    mongodb_repository,
)

Decorator = Callable[[Callable[..., Any]], Callable[..., Any]]


def compose(*decorators: Decorator) -> Decorator:
    def decorated(fn: Callable[..., Any]) -> Callable[..., Any]:
        for deco in reversed(decorators):
            fn = deco(fn)

        return fn

    return decorated


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
