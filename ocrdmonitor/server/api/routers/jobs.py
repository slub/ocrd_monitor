from fastapi import APIRouter, Response, Depends

from ocrdmonitor.protocols import Environment, OcrdJob, Repositories

from typing import List

from ocrdmonitor.ocrdcontroller import OcrdController

class ResultList:
    def __init__(self, results: List[OcrdJob]):
        self.results = results


def router(environment: Environment) -> None:
    router = APIRouter(prefix="/jobs")

    @router.get("/", name="api.jobs")
    async def jobs(
        repositories: Repositories = Depends(environment.repositories),
    ) -> Response:
        job_repository = repositories.ocrd_jobs
        jobs = await job_repository.find_all()
        
        return ResultList(jobs)

    @router.get("/{job_id}", name="api.job")
    async def job(
        repositories: Repositories = Depends(environment.repositories),
    ) -> Response:
        job_repository = repositories.ocrd_jobs
        jobs = await job_repository.find_all()
        
        return ResultList(jobs)

    @router.get("/{job_id}/processstatus", name="api.job.processstatus")
    async def job_processstatus(
        job_id: str, repositories: Repositories = Depends(environment.repositories)
    ) -> Response:
        controller = OcrdController(environment.controller_server())

        job_repository = repositories.ocrd_jobs
        job = await job_repository.get(job_id)
        return await controller.status_for(job)

    return router
