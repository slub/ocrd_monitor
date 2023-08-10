from ocrdmonitor.environment import ProductionEnvironment
from ocrdmonitor.server.settings import Settings
from ocrdmonitor.server.app import create_app

settings = Settings()
environment = ProductionEnvironment(settings)
app = create_app(environment)
