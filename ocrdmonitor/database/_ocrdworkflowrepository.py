from dataclasses import asdict
import pymongo
from beanie import Document

from pathlib import Path

from ocrdmonitor.protocols import OcrdWorkflow, OcrdWorkflowStatus


class MongoOcrdWorkflow(Document):
    name: str
    file: Path
    status: OcrdWorkflowStatus

    class Settings:
        name = "OcrdWorkflow"
        indexes = [
            pymongo.IndexModel(
                [
                    ("process_dir", pymongo.ASCENDING),
                    ("time_created", pymongo.DESCENDING),
                ]
            )
        ]


class MongoWorkflowRepository:
    async def insert(self, workflow: OcrdWorkflow) -> None:
        await MongoOcrdWorkflow(**asdict(workflow)).insert()  # type: ignore

    async def update(self, workflow: OcrdWorkflow) -> None:
        await MongoOcrdWorkflow(**asdict(workflow)).update()  # type: ignore

    async def find_all(self) -> list[OcrdWorkflow]:
        return [
            OcrdWorkflow(**j.dict(exclude={"id"}))
            for j in await MongoOcrdWorkflow.find_all().to_list()
        ]
