from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import Response

import ocrdmonitor.sshremote
from ocrdmonitor.database._ocrdjobrepository import OcrdJob
from ocrdmonitor.processstatus import ProcessState, ProcessStatus
from ocrdmonitor.sshremote import SSHConfig
from tests.ocrdmonitor.server import scraping
from tests.ocrdmonitor.server.fixtures.environment import Fixture
from tests.ocrdmonitor.server.fixtures.repository import mongodb_repository
from tests.ocrdmonitor.server.fixtures.settings import JOB_DIR


@pytest.fixture(autouse=True)
def prepare_and_clean_files() -> Generator[None, None, None]:
    JOB_DIR.mkdir(exist_ok=True)

    yield

    for jobfile in JOB_DIR.glob("*"):
        jobfile.unlink()

    JOB_DIR.rmdir()


def job_template() -> OcrdJob:
    created_at = datetime(2023, 4, 12, hour=13, minute=0, second=0)
    terminated_at = created_at + timedelta(hours=1)
    return OcrdJob(
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


@pytest_asyncio.fixture
async def app() -> AsyncIterator[TestClient]:
    fixture = Fixture().with_repository_type(mongodb_repository)
    async with fixture as env:
        yield env.app


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize(
    argnames=["return_code", "result_text"],
    argvalues=[(0, "SUCCESS"), (1, "FAILURE")],
)
async def test__given_a_completed_ocrd_job__the_job_endpoint_lists_it_in_a_table(
    app: TestClient,
    return_code: int,
    result_text: str,
) -> None:
    completed_job = job_template()
    completed_job.return_code = return_code
    await completed_job.insert()

    response = app.get("/jobs/")

    assert response.is_success
    assert_lists_completed_job(completed_job, result_text, response)


@pytest.mark.asyncio
@pytest.mark.integration
async def test__given_a_running_ocrd_job__the_job_endpoint_lists_it_with_resource_consumption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = 1234
    expected_status = make_status(pid)
    patch_controller(monkeypatch, expected_status)

    fixture = Fixture().with_repository_type(mongodb_repository)
    async with fixture as env:
        app = env.app
        job = await running_ocrd_job(pid)

        response = app.get("/jobs/")

        assert response.is_success
        assert_lists_running_job(job, expected_status, response)


def make_status(pid: int) -> ProcessStatus:
    expected_status = ProcessStatus(
        pid=pid,
        state=ProcessState.RUNNING,
        percent_cpu=0.25,
        memory=1024,
        cpu_time=timedelta(seconds=10, minutes=5, hours=1),
    )

    return expected_status


async def running_ocrd_job(pid: int) -> OcrdJob:
    running_job = job_template()
    running_job.pid = pid
    await running_job.insert()

    return running_job


def patch_controller(
    monkeypatch: pytest.MonkeyPatch, expected_status: ProcessStatus
) -> None:
    class ControllerStub:
        def __init__(self, _: SSHConfig) -> None:
            pass

        async def read_file(self, path: str) -> str:
            return str(expected_status.pid)

        async def process_status(self, process_group: int) -> list[ProcessStatus]:
            return [expected_status]

    monkeypatch.setattr(ocrdmonitor.sshremote, "SSHRemote", RemoteStub)
    print(ocrdmonitor.sshremote.SSHRemote)


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
