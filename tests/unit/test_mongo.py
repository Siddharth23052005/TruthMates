import pytest

from db import mongo


@pytest.mark.asyncio
async def test_save_validated_posts_uses_analysis_key(monkeypatch):
    class FakeUpdateCollection:
        def __init__(self) -> None:
            self.operations = []

        async def update_one(self, *, filter, update, upsert):
            self.operations.append({"filter": filter, "update": update, "upsert": upsert})

    collection = FakeUpdateCollection()

    class FakeDatabase(dict):
        def __getitem__(self, key):
            return collection

    monkeypatch.setattr(mongo, "get_db", lambda: FakeDatabase())

    processed = await mongo.save_validated_posts(
        [
            {
                "claim": "Claim A",
                "analysis_key": "analysis-key-1",
                "source_ref": "manual://1",
                "input_type": "text",
                "verdict": "SUPPORTED",
            }
        ]
    )

    assert processed == 1
    assert collection.operations[0]["filter"] == {"analysis_key": "analysis-key-1"}
    assert collection.operations[0]["upsert"] is True


@pytest.mark.asyncio
async def test_save_validated_posts_backfills_analysis_key(monkeypatch):
    class FakeUpdateCollection:
        def __init__(self) -> None:
            self.operations = []

        async def update_one(self, *, filter, update, upsert):
            self.operations.append({"filter": filter, "update": update, "upsert": upsert})

    collection = FakeUpdateCollection()

    class FakeDatabase(dict):
        def __getitem__(self, key):
            return collection

    monkeypatch.setattr(mongo, "get_db", lambda: FakeDatabase())

    await mongo.save_validated_posts(
        [
            {
                "claim": "Claim B",
                "input_type": "text",
                "source_ref": "manual://2",
                "verdict": "UNVERIFIED",
            }
        ]
    )

    written = collection.operations[0]["update"]["$set"]
    assert written["analysis_key"]
    assert written["source_ref"] == "manual://2"
