import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ocrdmonitor.ocrdcontroller import OcrdController
from ocrdmonitor.server.index import create_index
from ocrdmonitor.server.jobs import create_jobs
from ocrdmonitor.server.logs import create_logs
from ocrdmonitor.server.logview import create_logview
from ocrdmonitor.server.settings import Settings
from ocrdmonitor.server.workflows import create_workflows
from ocrdmonitor.server.workspaces import create_workspaces

PKG_DIR = Path(__file__).parent
STATIC_DIR = PKG_DIR / "static"
TEMPLATE_DIR = PKG_DIR / "templates"


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI()
    templates = Jinja2Templates(TEMPLATE_DIR)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(Exception)
    async def swallow_exceptions(request: Request, err: Exception) -> Response:
        logging.error(err)
        return RedirectResponse("/")

    app.include_router(create_index(templates))
    app.include_router(
        create_jobs(
            templates,
            OcrdController(
                settings.ocrd_controller.process_query(),
                settings.ocrd_controller.job_dir,
            ),
        )
    )
    app.include_router(
        create_workspaces(
            templates,
            settings.ocrd_browser.factory(),
            settings.ocrd_browser.workspace_dir,
        )
    )
    app.include_router(create_logs(templates, settings.ocrd_browser.workspace_dir))
    app.include_router(create_workflows(templates))
    app.include_router(create_logview(templates, settings.ocrd_logview.port))

    return app
