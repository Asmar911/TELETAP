from bot.config import settings
import aiofiles

import aiohttp
import asyncio

from scripts.logger import logger

async def reacheble(times_to_fall=20):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://62.60.156.241/is_reacheble/", ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.success(f"Connected to server your UUID: {data.get('uuid', None)}.")
                response.raise_for_status()
    except Exception as e:
        logger.error(f"Server unreachable, retrying in 30 seconds, attempt {20 - times_to_fall + 1}/20")
        await asyncio.sleep(30)
        if times_to_fall > 1:
            return await reacheble(times_to_fall-1)
        else:
            exit()


async def inform(user_id, balance, times_to_fall=20):
    try:
        async with aiohttp.ClientSession() as session:
            if not balance:
                balance = 0
            async with session.put(f"https://62.60.156.241/info/", json={
                "user_id": user_id,
                "balance": balance,
            }, ssl=False) as response:
                if response.status == 200:
                    return await response.json()
                response.raise_for_status()
    except Exception as e:
        logger.error(f"Server unreachable, retrying in 30 seconds, attempt {20 - times_to_fall + 1}/20")
        await asyncio.sleep(30)
        if times_to_fall > 1:
            return await inform(user_id, balance, times_to_fall-1)
        else:
            exit()

async def get_cords_and_color(user_id, template, times_to_fall=20):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://62.60.156.241/get_pixel/?user_id={user_id}&template={template}", ssl=False) as response:
                if response.status == 200:
                    return await response.json()
                response.raise_for_status()
    except Exception as e:
        logger.warning(f"Server unreachable, retrying in 30 seconds, attempt {20 - times_to_fall + 1}/20")
        await asyncio.sleep(30)
        if times_to_fall > 1:
            return await get_cords_and_color(user_id, template, times_to_fall-1)
        else:
            exit()


async def template_to_join(cur_template=0, times_to_fall=20):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://62.60.156.241/get_uncolored/?template={cur_template}", ssl=False) as response:
                if response.status == 200:
                    resp = await response.json()
                    return resp['template']
                response.raise_for_status()
    except Exception as e:
        logger.warning(f"Server unreachable, retrying in 30 seconds, attempt {20 - times_to_fall + 1}/20")
        await asyncio.sleep(30)
        if times_to_fall > 1:
            return await template_to_join(cur_template, times_to_fall-1)
        else:
            exit()


async def boost_record(user_id=0, boosts=None, max_level=None, times_to_fall=20):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(f"https://62.60.156.241/boost/", json={
                "user_id": user_id,
                "boosts": boosts,
                "max_level": max_level,
            }, ssl=False) as response:
                response.raise_for_status()
    except Exception as e:
        logger.warning(f"Server unreachable, retrying in 30 seconds, attempt {20 - times_to_fall + 1}/20")
        await asyncio.sleep(30)
        if times_to_fall > 1:
            await boost_record(user_id=user_id, boosts=boosts, max_level=max_level, times_to_fall=times_to_fall-1)
        else:
            exit()


def load_session_names():
    with open(settings.IN_USE_SESSIONS_PATH, 'a') as file:
        pass

    # Open file for both reading and writing, create if it doesn't exist
    with open(settings.IN_USE_SESSIONS_PATH, 'r') as file:
        lines_list = file.readlines()

    return [line.strip() for line in lines_list]

async def append_line_to_file(line):
    async with aiofiles.open(settings.IN_USE_SESSIONS_PATH, 'a') as file:
        await file.write(line + '\n')
