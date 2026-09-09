import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-everything"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.list_tools()
            for t in response.tools:
                print(dir(t))
                break

if __name__ == "__main__":
    asyncio.run(main())
