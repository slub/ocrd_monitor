from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

def register_listroutes(
    router: APIRouter, templates: Jinja2Templates
) -> None:
    
    @router.get("/", name="workspaces.list")
    def list_workspaces(request: Request) -> Response:
        return templates.TemplateResponse(
            "list.html.j2",
            {"request": request, "title": "Workspaces"},
        )
    