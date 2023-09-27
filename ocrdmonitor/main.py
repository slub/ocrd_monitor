from ocrdmonitor.environment import ProductionEnvironment

from ocrdmonitor.server import lifespan
from ocrdmonitor.server.app import create_app
from ocrdmonitor.server.lifespan import processtimeout, unreachable_cleanup
from ocrdmonitor.server.settings import Settings


settings = Settings()
environment = ProductionEnvironment(settings)
app = create_app(
    environment,
    lifespan.create(
        setup=[unreachable_cleanup.clean_unreachable_browsers(environment)],
        background=[processtimeout.expiration_loop(environment)],
    ),
)
