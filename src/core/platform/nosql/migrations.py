from typing import List
from uuid import uuid4


class Migration:
    def __init__(self, version: int, up: callable):
        self.version = version
        self.up = up


def execute_migrations() -> List[Migration]:
    return [
        Migration(
            version=1,
            up=lambda db: db["profiles"].update_many(
                {},
                {"$set": {"is_active": True}}
            )
        ),
        Migration(
            version=2,
            up=lambda db: db["profiles"].update_many(
                {},
                {"$set": {"iteration_limit": 100}}
            )
        ),
        Migration(
            version=3,
            up=lambda db: db["profiles"].update_many(
                {},
                {"$set": {"files": []}}
            )
        ),
        Migration(
            version=4,
            up=lambda db: db["conversations"].update_many(
                {},
                {"$set": {"client_id": str(uuid4())}}
            )
        ),
        Migration(
            version=5,
            up=lambda db: db["profiles"].update_many(
                {},
                {"$set": {"role": "seller"}}
            )
        ),
        Migration(
            version=6,
            up=lambda db: db["conversations"].update_many(
                {"is_sandbox": {"$exists": False}},
                {"$set": {"is_sandbox": False}}
            )
        ),
        Migration(
            version=7,
            up=lambda db: db["faqs"].update_many(
                {"profile_id": {"$exists": False}},
                {"$set": {"profile_id": None}}
            )
        ),
    ]
