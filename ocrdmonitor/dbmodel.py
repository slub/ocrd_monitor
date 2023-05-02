import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie


class BrowserProcess(Document):
    owner: str
    process_id: str
    workspace: str

    class Settings:
        indexes = [
            pymongo.IndexModel(
                [
                    ("owner", pymongo.ASCENDING),
                    ("workspace", pymongo.ASCENDING),
                ]
            )
        ]


async def init(connection_str: str) -> None:
    client: AsyncIOMotorClient = AsyncIOMotorClient(connection_str)
    await init_beanie(
        database=client.browsers,
        document_models=[BrowserProcess],  # type: ignore
    )
