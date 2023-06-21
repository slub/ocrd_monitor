from __future__ import annotations
from typing import Awaitable, Callable, Generic, Iterable, NamedTuple, TypeVar, Union


class NoPortsAvailableError(RuntimeError):
    pass


T = TypeVar("T")


class PortBindingError(RuntimeError):
    pass


PortBindingResult = Union[T, PortBindingError]
PortBinding = Callable[[str, int], Awaitable[PortBindingResult[T]]]


class BoundPort(NamedTuple, Generic[T]):
    bound_app: T
    port: int


async def try_bind(
    binding: PortBinding[T], host: str, ports: Iterable[int]
) -> BoundPort[T]:
    for port in ports:
        result = await binding(host, port)
        if isinstance(result, PortBindingError):
            continue

        return BoundPort(result, port)

    raise NoPortsAvailableError()
