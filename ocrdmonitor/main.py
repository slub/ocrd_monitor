import signal
from ocrdmonitor.environment import ProductionEnvironment
from ocrdmonitor.processtimeout import browser_cleanup_process
from ocrdmonitor.server.settings import Settings
from ocrdmonitor.server.app import create_app


background_process = browser_cleanup_process()
background_process.launch()

# signal.signal(signal.SIGKILL, lambda *args, **kwargs: background_process.shutdown)

settings = Settings()
environment = ProductionEnvironment(settings)
app = create_app(environment)
