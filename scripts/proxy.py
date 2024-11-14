import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from scripts.logger import logger




async def check_proxy(http_client: aiohttp.ClientSession, proxy: Proxy , session_name) -> None:
        try:
            response = await http_client.get(url='https://ipinfo.io/ip', timeout=aiohttp.ClientTimeout(10))
            ip = (await response.text())
            logger.info(f"{session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{session_name} | Proxy: {proxy} | Error: {error}")

    