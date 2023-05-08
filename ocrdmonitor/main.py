import asyncio
from ocrdmonitor.server.settings import Settings
from ocrdmonitor.server.app import create_app

settings = Settings()
app = asyncio.get_event_loop().run_until_complete(create_app(settings))
