from __future__ import annotations

import asyncio
from difflib import SequenceMatcher
from typing import Awaitable, Callable

from fastapi import Response

from ocrdbrowser import Channel, ChannelClosed, OcrdBrowser


async def forward(browser: OcrdBrowser, partial_workspace: str) -> Response:
    url = _get_redirect_url(browser, partial_workspace)
    resource = await browser.client().get(url)
    return Response(content=resource)


def _get_redirect_url(browser: OcrdBrowser, partial_workspace: str) -> str:
    matcher = SequenceMatcher(None, browser.workspace(), partial_workspace)
    match = matcher.find_longest_match()
    return partial_workspace[match.size :]


CloseCallback = Callable[[OcrdBrowser], Awaitable[None]]


async def communicate_until_closed(
    websocket: Channel, browser: OcrdBrowser, close_callback: CloseCallback
) -> None:
    async with browser.client().open_channel() as channel:
        try:
            while True:
                await _tunnel(channel, websocket)
        except ChannelClosed:
            await close_callback(browser)
        except Exception:
            pass


async def _tunnel(
    source: Channel,
    target: Channel,
    timeout: float = 0.001,
) -> None:
    await _tunnel_one_way(source, target, timeout)
    await _tunnel_one_way(target, source, timeout)


async def _tunnel_one_way(
    source: Channel,
    target: Channel,
    timeout: float,
) -> None:
    try:
        source_data = await asyncio.wait_for(source.receive_bytes(), timeout)
        await target.send_bytes(source_data)
    except asyncio.exceptions.TimeoutError:
        # a timeout is rather common if no data is being sent,
        # so we are simply ignoring this exception
        pass
