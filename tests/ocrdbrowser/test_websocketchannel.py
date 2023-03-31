import asyncio
from typing import Any, Coroutine, Protocol

import pytest

from ocrdbrowser import Channel, ChannelClosed, HttpBrowserClient
from tests.testdoubles import BackgroundProcess, broadway_fake


async def send(channel: Channel) -> None:
    return await channel.send_bytes(bytes())


async def receive(channel: Channel) -> bytes:
    return await channel.receive_bytes()


class CommunicationFunction(Protocol):
    def __call__(self, channel: Channel) -> Coroutine[Any, Any, Any]:
        ...


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("comm_function", [send, receive])
async def test__channel__losing_connection_while_communicating__raises_channel_closed(
    comm_function: CommunicationFunction,
) -> None:
    server = broadway_fake("")
    await asyncio.to_thread(server.launch)

    sut = HttpBrowserClient("http://localhost:7000")
    with pytest.raises(ChannelClosed):
        async with sut.open_channel() as channel:
            await shutdown_server(server)
            await comm_function(channel)


async def shutdown_server(server: BackgroundProcess) -> None:
    await asyncio.to_thread(server.shutdown)

    # TODO:
    # it seems we need a short delay for the socket connection to close
    # can we find a better solution for that?
    await asyncio.sleep(1)
