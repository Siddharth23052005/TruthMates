import asyncio
import json
from db.mongo import get_db
from bson import json_util

async def main():
    docs = await get_db()['social_monitor'].find().to_list(1)
    print(json.dumps(docs, default=json_util.default, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
