import asyncio

import aiohttp


session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
r = asyncio.run(session.get('https://www6b3.wolframalpha.com/Calculate/MSP/MSP2361h5431b06g574g1200002f73d9c30943fi2i?MSPStoreType=image/gif&s=6'))
r = asyncio.run(r.content.read())
print(r)