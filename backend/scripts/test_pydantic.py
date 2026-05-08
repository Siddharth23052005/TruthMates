import asyncio
from db.mongo import get_db
from models.social_schemas import MonitorEntry

async def main():
    docs = await get_db()['social_monitor'].find().to_list(1)
    doc = docs[0]
    doc.pop('_id', None)
    try:
        entry = MonitorEntry(**doc)
        print("Success!")
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
