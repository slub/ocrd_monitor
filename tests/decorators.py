from typing import Any, Callable


Decorator = Callable[[Callable[..., Any]], Callable[..., Any]]


def compose(*decorators: Decorator) -> Decorator:
    def decorated(fn: Callable[..., Any]) -> Callable[..., Any]:
        for deco in reversed(decorators):
            fn = deco(fn)

        return fn

    return decorated
