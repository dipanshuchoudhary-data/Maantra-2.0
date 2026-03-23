import os
import asyncio

async def main():
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

    if not token:
        raise ValueError("Missing GITHUB_PERSONAL_ACCESS_TOKEN")

    print("GitHub MCP server started")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())