from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import patch

from ocrdmonitor.server.settings import OcrdBrowserSettings
from tests.testdoubles import BrowserTestDoubleFactory


@asynccontextmanager
async def patch_factory(
    factory: BrowserTestDoubleFactory,
) -> AsyncIterator[BrowserTestDoubleFactory]:
    async with factory:
        with patch.object(OcrdBrowserSettings, "factory", lambda _: factory):
            yield factory
