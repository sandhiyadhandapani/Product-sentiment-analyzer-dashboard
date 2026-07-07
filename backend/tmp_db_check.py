import asyncio
from database import connect_to_mongo, close_mongo_connection

async def main():
    db = await connect_to_mongo()
    print('DB_NAME', db.name)
    print(await db.command('ping'))
    await close_mongo_connection()

asyncio.run(main())
