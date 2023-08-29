from pathlib import Path
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates


def create_workflows(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter(prefix="/workflows")

    @router.get("/", name="workflows")
    async def workflows(request: Request) -> Response:
        return templates.TemplateResponse("workflows.html.j2", {"request": request})


    @router.get("/{id}", name="workflows.detail")
    def detail(request: Request, path: Path) -> Response:
        if not path.exists() or path.is_dir():
            return Response(status_code=404)

        return templates.TemplateResponse(
            "workflow_details.html.j2",
            {"request": request, "workflow": path.read_text()},
        )

    @router.get("/detail/{path:path}", name="workflows.detail")
    def detail(request: Request, path: Path) -> Response:
        if not path.exists() or path.is_dir():
            return Response(status_code=404)

        return templates.TemplateResponse(
            "workflow_details.html.j2",
            {"request": request, "workflow": path.read_text()},
        )

    return router
