from __future__ import annotations
from dataclasses import replace

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import status
from httpx import Response
import json
import pytest
from pytest_httpx import HTTPXMock

from ocrdmonitor.processstatus import ProcessState, ProcessStatus
from ocrdmonitor.protocols import OcrdJob
from tests.ocrdmonitor.server import scraping
from tests.ocrdmonitor.fixtures.environment import Fixture


def job_template() -> OcrdJob:
    created_at = datetime(2023, 4, 12, hour=13, minute=0, second=0)
    terminated_at = created_at + timedelta(hours=1)
    return OcrdJob(
        pid=None,
        return_code=None,
        process_id="5432",
        task_id="45989",
        process_dir=Path("/data/5432"),
        workdir=Path("ocr-d/data/5432"),
        workflow_file=Path("ocr-workflow-default.sh"),
        remotedir="/remote/job/dir",
        controller_address="controller.ocrdhost.com",
        time_created=created_at,
        time_terminated=terminated_at,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    argnames=["return_code", "result_text"],
    argvalues=[(0, "SUCCESS"), (1, "FAILURE")],
)
async def test__given_a_completed_ocrd_job__the_job_endpoint_lists_it_in_a_table(
    repository_fixture: Fixture,
    return_code: int,
    result_text: str,
) -> None:
    async with repository_fixture as env:
        completed_job = replace(job_template(), return_code=return_code)
        await env._repositories.ocrd_jobs.insert(completed_job)

        response = env.app.get("/jobs/")

        assert response.is_success
        assert_lists_completed_job(completed_job, result_text, response)


@pytest.mark.asyncio
async def test__given_a_running_ocrd_job__the_job_endpoint_lists_it_with_resource_consumption(
    repository_fixture: Fixture,
) -> None:
    pid = 1234
    expected_status = make_status(pid)
    remote_stub = RemoteServerStub(expected_status)
    fixture = repository_fixture.with_controller_remote(remote_stub)

    async with fixture as env:
        app = env.app
        job = running_ocrd_job(pid)
        await env._repositories.ocrd_jobs.insert(job)

        response = app.get("/jobs/")

        assert response.is_success
        assert_lists_running_job(job, expected_status, response)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    argnames=["status_code", "message", "httpx_mock_status_code"],
    argvalues=[
        (status.HTTP_200_OK, "Job successfully canceled", status.HTTP_200_OK),
        (
            status.HTTP_409_CONFLICT,
            "Job could not be canceled.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),
    ],
)
async def test__kill_ocrd_job(
    repository_fixture: Fixture,
    httpx_mock: HTTPXMock,
    status_code: int,
    message: str,
    httpx_mock_status_code: int,
) -> None:
    pid = 1234
    async with repository_fixture as env:
        httpx_mock.add_response(
            method="GET",
            url=f"{env.settings.ocrd_manager.url}/cancel_job/{pid}",
            status_code=httpx_mock_status_code,
        )
        response = env.app.get(f"/jobs/kill/{pid}/")
        assert response.status_code == status_code
        assert json.loads(response.content)["message"] == message


@pytest.fixture
def non_mocked_hosts() -> list[str]:
    return ["testserver"]


def make_status(pid: int) -> ProcessStatus:
    expected_status = ProcessStatus(
        pid=pid,
        state=ProcessState.RUNNING,
        percent_cpu=0.25,
        memory=1024,
        cpu_time=timedelta(seconds=10, minutes=5, hours=1),
    )

    return expected_status


class RemoteServerStub:
    def __init__(self, expected_status: ProcessStatus) -> None:
        self.expected_status = expected_status

    async def read_file(self, path: str) -> str:
        return str(self.expected_status.pid)

    async def process_status(self, process_group: int) -> list[ProcessStatus]:
        return [self.expected_status]


def running_ocrd_job(pid: int) -> OcrdJob:
    running_job = replace(job_template(), pid=pid)
    return running_job


def assert_lists_completed_job(
    completed_job: OcrdJob, result_text: str, response: Response
) -> None:
    texts = collect_texts_from_job_table(response.content, "completed-jobs")

    assert texts == [
        str(completed_job.time_terminated),
        str(completed_job.task_id),
        str(completed_job.process_id),
        completed_job.workflow_file.name,
        f"{completed_job.return_code} ({result_text})",
        completed_job.process_dir.name,
        "ocrd.log",
    ]


def assert_lists_running_job(
    running_job: OcrdJob,
    process_status: ProcessStatus,
    response: Response,
) -> None:
    texts = collect_texts_from_job_table(response.content, "running-jobs")

    assert texts == [
        str(running_job.time_created),
        str(running_job.task_id),
        str(running_job.process_id),
        running_job.workflow_file.name,
        str(process_status.pid),
        str(process_status.state),
        str(process_status.percent_cpu),
        str(process_status.memory),
        str(process_status.cpu_time),
    ]


def collect_texts_from_job_table(content: bytes, table_id: str) -> list[str]:
    selector = f"#{table_id} td:not(:has(a)):not(:has(button)), #{table_id} td > a"
    return scraping.parse_texts(content, selector)
