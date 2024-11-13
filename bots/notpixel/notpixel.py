import asyncio
from random import randint
from typing import Any
from better_proxy import Proxy
from bot.config import settings
from scripts.accounts import Accounts
from scripts.registrator import get_tg_client
from bot.tapper import run_tapper
from scripts.logger import logger
from bot.scripts import load_session_names

def get_proxy(raw_proxy: str) -> Proxy:
    return Proxy.from_str(proxy=raw_proxy).as_url if raw_proxy else None

async def main():
    accounts = await Accounts().ready_accounts()
    used_session_names = load_session_names()
    tasks = []
    for account in accounts:
        session_name, user_agent, raw_proxy = account.values()
        first_run = session_name not in used_session_names
        tg_client = await get_tg_client(session_name=session_name, proxy=raw_proxy, workdir=settings.WORKDIR)
        proxy = get_proxy(raw_proxy=raw_proxy)
        tasks.append(asyncio.create_task(run_tapper(tg_client=tg_client, user_agent=user_agent, proxy=proxy, first_run=first_run)))
        if settings.ACCOUNTS_MOOD_SEQUENTIAL:
            await asyncio.sleep(delay=randint(*settings.LOGIN_SLEEP))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())