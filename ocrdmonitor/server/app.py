import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ocrdmonitor.protocols import Environment
from ocrdmonitor.server.index import create_index
from ocrdmonitor.server.jobs import create_jobs
from ocrdmonitor.server.lifespan import lifespan
from ocrdmonitor.server.logs import create_logs
from ocrdmonitor.server.logview import create_logview
from ocrdmonitor.server.workflows import create_workflows
from ocrdmonitor.server.workspaces import create_workspaces

PKG_DIR = Path(__file__).parent
STATIC_DIR = PKG_DIR / "static"
TEMPLATE_DIR = PKG_DIR / "templates"


def create_app(environment: Environment) -> FastAPI:
    app = FastAPI(lifespan=lifespan(environment))
    templates = Jinja2Templates(TEMPLATE_DIR)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(Exception)
    async def swallow_exceptions(request: Request, err: Exception) -> Response:
        logging.error(err)
        return RedirectResponse("/")

    @app.exception_handler(RequestValidationError)
    async def validation_exception(
        request: Request, exc: RequestValidationError
    ) -> Response:
        logging.error(f"Unprocessable entity on route {request.url}")
        logging.error("Error details:")
        logging.error(exc.errors())
        logging.error(exc.body)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
        )

    app.include_router(create_index(templates))
    app.include_router(create_jobs(templates, environment))
    app.include_router(create_workspaces(templates, environment))
    app.include_router(
        create_logs(templates, environment.settings.ocrd_browser.workspace_dir)
    )
    app.include_router(create_workflows(templates, environment))
    app.include_router(
        create_logview(templates, environment.settings.ocrd_logview.port)
    )

    return app
