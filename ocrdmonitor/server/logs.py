from pathlib import Path
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

import ocrdmonitor.readlogs as readlogs

def create_logs(templates: Jinja2Templates, workspace_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/logs")

    @router.get("/view/{path:path}", name="logs.view")
    def logs(request: Request, path: Path) -> Response:
        # workspace_dir is /data/ocr-d, but job.workdir is relative to /data 
        # (includes ocr-d/ prefix)
        path = workspace_dir.parent / path
        if not readlogs.has_logs(path):
            return Response(status_code=404)

        content = readlogs.from_path(path)

        return templates.TemplateResponse(
            "logs.html.j2", {"request": request, "logs": content}
        )

    return router
