from dataclasses import asdict

from beanie import Document

from ocrdmonitor.protocols import OcrdWorkflow


class MongoOcrdWorkflow(Document):
    name: str

    class Settings:
        name = "OcrdWorkflow"

class MongoWorkflowRepository:
    async def insert(self, workflow: OcrdWorkflow) -> None:
        await MongoOcrdWorkflow(**asdict(workflow)).insert()  # type: ignore

    async def find_all(self) -> list[OcrdWorkflow]:
        return [
            OcrdWorkflow(**j.dict())
            for j in await MongoOcrdWorkflow.find_all().to_list()
        ]
    
    async def get(self, id:str ) -> OcrdWorkflow:
        return await MongoOcrdWorkflow.get(id)