from __future__ import annotations

import asyncio

from fastapi import Response
from ocrdbrowser import OcrdBrowser, Channel
from difflib import SequenceMatcher


def get_redirect_url(browser: OcrdBrowser, url: str) -> str:
    matcher = SequenceMatcher(None, browser.workspace(), url)
    match = matcher.find_longest_match()
    return url[match.size :]


async def forward(browser: OcrdBrowser, url: str) -> Response:
    url = get_redirect_url(browser, url)
    resource = await browser.client().get(url)
    return Response(content=resource)


async def tunnel(
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
