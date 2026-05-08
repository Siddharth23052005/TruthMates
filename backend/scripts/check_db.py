import asyncio
from db.mongo import get_db

async def main():
    count = await get_db()['social_monitor'].count_documents({})
    print("Count:", count)

if __name__ == "__main__":
    asyncio.run(main())
