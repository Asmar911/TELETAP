from pyrogram import Client

from scripts.file_manager import save_to_json
from scripts.logger import logger
from scripts.agents import generate_random_user_agent
from global_data.global_config import global_settings 


async def create_session() -> None:

    session_name = input('Enter the session name (press Enter to exit): ')

    if not session_name:
        return None

    raw_proxy = input("Input the proxy in the format type://user:pass:ip:port (press Enter to use without proxy): ")
    user_agent = input("Input the user agent: (press Enter to use random user agent): ")
    session = await get_tg_client(session_name=session_name, proxy=raw_proxy)
    async with session:
        user_data = await session.get_me()

    # user_agent = generate_random_user_agent(device_type='android', browser_type='chrome')
    save_to_json(f'global_data/sessions/accounts.json',
                 dict_={
                    "session_name": session_name,
                    "user_agent": user_agent if user_agent else generate_random_user_agent(device_type='android', browser_type='chrome'),
                    "proxy": raw_proxy if raw_proxy else None
                 })
    logger.success(f'Session added successfully @{user_data.username}')
    again = input("Do you want to add another session? (y/n): ")

    if 'y' in again.lower():
        await create_session()


async def get_tg_client(session_name: str, proxy: str | None) -> Client:
    if not session_name:
        raise FileNotFoundError(f"{session_name} NOT FOUND")

    if not global_settings.API_ID or not global_settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    proxy_dict = {
        "scheme": proxy.split(":")[0],
        "username": proxy.split(":")[1].split("//")[1],
        "password": proxy.split(":")[2],
        "hostname": proxy.split(":")[3],
        "port": int(proxy.split(":")[4])
    } if proxy else None
    try:
        tg_client = Client(
            name=session_name,
            api_id=global_settings.API_ID,
            api_hash=global_settings.API_HASH,
            workdir="global_data/sessions/",
            # plugins=dict(root="bot/plugins"),
            proxy=proxy_dict
        )
        return tg_client

    except Exception as e:
        logger.error(f"{session_name} | Error occurred during getting tg_client: {e}")

    return tg_client




async def validate_account(accounts):
        for account in accounts:
            tg_client = await get_tg_client(session_name=account['session_name'], proxy=account['proxy'])
            if not tg_client.is_connected:
                if await tg_client.connect():
                    await tg_client.join_chat("TELETAPBOTS")
                    await tg_client.disconnect()

           