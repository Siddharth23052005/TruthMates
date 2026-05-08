import asyncio
from db.mongo import get_db
from models.social_schemas import MonitorEntry

async def main():
    docs = await get_db()['social_monitor'].find().to_list(100)
    failed = 0
    for doc in docs:
        doc.pop('_id', None)
        try:
            MonitorEntry(**doc)
        except Exception as e:
            failed += 1
            print(f"Failed doc ID: {doc.get('entry_id')}. Error: {e}")
    print(f"Total: {len(docs)}, Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
