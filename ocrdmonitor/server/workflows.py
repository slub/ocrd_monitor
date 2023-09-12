from pathlib import Path
from fastapi import APIRouter, Request, Response, Depends
from fastapi.templating import Jinja2Templates

from ocrdmonitor.protocols import OcrdWorkflow, Environment, Repositories


def create_workflows(templates: Jinja2Templates, environment: Environment) -> APIRouter:
    router = APIRouter(prefix="/workflows")

    @router.get("/", name="workflows")
    async def workflows(
        request: Request, repositories: Repositories = Depends(environment.repositories)
    ) -> Response:
        workflows = await repositories.ocrd_workflows.find_all()

        return templates.TemplateResponse(
            "workflows.html.j2", {"request": request, "workflows": workflows}
        )

    @router.get("/create", name="workflows.create.form")
    async def workflow_create_form(request: Request) -> Response:
        return templates.TemplateResponse(
            "workflow_form.html.j2", {"request": request, "workflow": dict()}
        )

    @router.get("/{workflow_id}/edit", name="workflows.edit.form")
    async def workflow_edit_form(
        workflow_id: str,
        request: Request,
        repositories: Repositories = Depends(environment.repositories),
    ) -> Response:
        workflow = await repositories.ocrd_workflows.get(workflow_id)
        return templates.TemplateResponse(
            "workflow_form.html.j2", {"request": request, "workflow": workflow}
        )

    @router.post("/", name="workflows.create")
    async def create_workflow(
        workflow: OcrdWorkflow,
        repositories: Repositories = Depends(environment.repositories),
    ) -> Response:
        await repositories.ocrd_workflows.insert(workflow)
        return workflow

    @router.get("/{workflow_id}", name="workflows.view")
    async def view(
        workflow_id: str,
        request: Request,
        repositories: Repositories = Depends(environment.repositories),
    ) -> Response:
        workflow = await repositories.ocrd_workflows.get(workflow_id)
        return templates.TemplateResponse(
            "workflow_details.html.j2",
            {"request": request, "workflow": workflow},
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
