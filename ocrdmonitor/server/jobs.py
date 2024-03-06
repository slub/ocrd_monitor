from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from ocrdmonitor.protocols import Environment, OcrdJob, Repositories

import httpx
import logging


def split_into_running_and_completed(
    jobs: Iterable[OcrdJob],
) -> tuple[list[OcrdJob], list[OcrdJob]]:
    running_ocrd_jobs = [job for job in jobs if job.is_running]
    completed_ocrd_jobs = [job for job in jobs if job.is_completed]
    return running_ocrd_jobs, completed_ocrd_jobs


def create_jobs(
    templates: Jinja2Templates,
    environment: Environment,
) -> APIRouter:
    router = APIRouter(prefix="/jobs")

    @router.get("/", name="jobs")
    async def jobs(
        request: Request, repositories: Repositories = Depends(environment.repositories)
    ) -> Response:
        job_repository = repositories.ocrd_jobs
        jobs = await job_repository.find_all()
        running, completed = split_into_running_and_completed(jobs)

        now = datetime.now(timezone.utc)
        return templates.TemplateResponse(
            "jobs.html.j2",
            {
                "request": request,
                "running_jobs": sorted(
                    running,
                    key=lambda x: x.time_created or now,
                ),
                "completed_jobs": sorted(
                    completed,
                    key=lambda x: x.time_terminated or now,
                ),
            },
        )

    @router.get("/kill/{job_pid}", name="jobs.kill")
    async def kill(job_pid: int) -> Response:
        status_code = status.HTTP_200_OK
        message="Job successfully canceled"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    environment.settings.ocrd_manager.url + f"/cancel_job/{job_pid}"
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = status.HTTP_409_CONFLICT
            message = "Job could not be canceled."
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url!r}."
            )

        return JSONResponse(status_code=status_code, content=dict(message=message))

    return router
