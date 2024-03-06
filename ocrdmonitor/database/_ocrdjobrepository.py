from dataclasses import asdict
import pymongo
from beanie import Document


from datetime import datetime
from pathlib import Path

from ocrdmonitor.protocols import OcrdJob


class MongoOcrdJob(Document):
    pid: int | None = None
    return_code: int | None = None
    time_created: datetime | None = datetime.now()
    time_terminated: datetime | None = None
    process_id: str
    task_id: str
    process_dir: Path
    workdir: Path
    remotedir: str
    workflow_file: Path

    class Settings:
        name = "OcrdJob"
        indexes = [
            pymongo.IndexModel(
                [
                    ("process_dir", pymongo.ASCENDING),
                    ("time_created", pymongo.DESCENDING),
                ]
            )
        ]


class MongoJobRepository:
    async def insert(self, job: OcrdJob) -> None:
        await MongoOcrdJob(**asdict(job)).insert()  # type: ignore

    async def find_all(self) -> list[OcrdJob]:
        return [OcrdJob(**j.dict(exclude={"id"})) for j in await MongoOcrdJob.find_all().to_list()]
