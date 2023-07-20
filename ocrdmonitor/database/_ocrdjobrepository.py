import pymongo
from beanie import Document


from datetime import datetime
from pathlib import Path


class OcrdJob(Document):
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
    controller_address: str

    class Settings:
        indexes = [
            pymongo.IndexModel(
                [
                    ("process_dir", pymongo.ASCENDING),
                    ("time_created", pymongo.DESCENDING),
                ]
            )
        ]
