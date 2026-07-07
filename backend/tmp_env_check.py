import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

for path in [Path('.env'), Path('..\\.env')]:
    print('ENV_EXISTS', str(path), path.exists())

load_dotenv(dotenv_path=Path('.env'))
uri = os.getenv('MONGODB_URI')
db = os.getenv('DATABASE_NAME')
print('ENV_FILE_USED', str(Path('.env').resolve()))
print('DATABASE_NAME', db)
if uri:
    parts = uri.split('@')
    if len(parts) > 1:
        userinfo = parts[0].split('://', 1)[1]
        user = userinfo.split(':', 1)[0]
        print('MONGODB_URI_MASKED', f'mongodb+srv://{user}:***@' + '@'.join(parts[1:]))
    else:
        print('MONGODB_URI_MASKED', uri)
else:
    print('MONGODB_URI_MASKED', None)

async def main():
    print('ATTEMPTING_PING')
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)
    try:
        await client.admin.command('ping')
        print('PING_OK')
    except Exception as exc:
        print('PING_FAILED', type(exc).__name__, str(exc))
        raise
    finally:
        client.close()

if __name__ == '__main__':
    asyncio.run(main())
