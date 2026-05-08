import asyncio
from services.social_monitor_service import get_monitor_entries

async def main():
    entries = await get_monitor_entries()
    print(f"Returned {len(entries)} entries")

if __name__ == "__main__":
    asyncio.run(main())
