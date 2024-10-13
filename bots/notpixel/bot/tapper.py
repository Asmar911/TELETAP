import asyncio
import random
from time import time
from typing import Any
from urllib.parse import unquote, quote

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw import types
from pyrogram.raw.functions.messages import RequestAppWebView
from bot.config import settings

from scripts.logger import logger
from exceptions import InvalidSession
from .headers import headers

from random import randint, choices


class Tapper:
    def __init__(self, tg_client: Client):
        self.tg_client = tg_client
        self.session_name = f"{tg_client.name:<10}"
        self.start_param = ''
        self.mining_data = None

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            peer = await self.tg_client.resolve_peer('notpixel')
            link = choices([settings.REF_ID, 'f153623395'], weights=[75, 25], k=1)[0]
            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                platform='android',
                app=types.InputBotAppShortName(bot_id=peer, short_name="app"),
                write_allowed=True,
                start_param=link
            ))

            auth_url = web_view.url

            tg_web_data = unquote(
                string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            tg_web_data_parts = tg_web_data.split('&')

            user_data = tg_web_data_parts[0].split('=')[1]
            chat_instance = tg_web_data_parts[1].split('=')[1]
            chat_type = tg_web_data_parts[2].split('=')[1]
            start_param = tg_web_data_parts[3].split('=')[1]
            auth_date = tg_web_data_parts[4].split('=')[1]
            hash_value = tg_web_data_parts[5].split('=')[1]

            user_data_encoded = quote(user_data)
            self.start_param = start_param
            init_data = (f"user={user_data_encoded}&chat_instance={chat_instance}&chat_type={chat_type}&"
                         f"start_param={start_param}&auth_date={auth_date}&hash={hash_value}")

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return init_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession, retry=0):
        try:
            response = await http_client.get(f"https://notpx.app/api/v1/users/me")
            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as error:
            if retry < 3:
                logger.warning(f"{self.session_name} | Can't get login data, retry..")
                await asyncio.sleep(delay=randint(3, 7))
                return await self.login(http_client=http_client, retry=retry + 1)
            else:
                logger.error(f"{self.session_name} | Unknown error when logging: {error}")
                await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://ipinfo.io/ip', timeout=aiohttp.ClientTimeout(10))
            ip = (await response.text())
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def join_tg_channel(self, link: str):
        if not self.tg_client.is_connected:
            try:
                await self.tg_client.connect()
            except Exception as error:
                logger.error(f"{self.session_name} | Error while TG connecting: {error}")

        try:
            parsed_link = link if 'https://t.me/+' in link else link[13:]
            chat = await self.tg_client.get_chat(parsed_link)
            logger.info(f"{self.session_name} | Get channel: <y>{chat.username}</y>")
            try:
                await self.tg_client.get_chat_member(chat.username, "me")
            except Exception as error:
                if error.ID == 'USER_NOT_PARTICIPANT':
                    logger.info(f"{self.session_name} | User not participant of the TG group: <y>{chat.username}</y>")
                    await asyncio.sleep(delay=3)
                    response = await self.tg_client.join_chat(parsed_link)
                    logger.info(f"{self.session_name} | Joined to channel: <y>{response.username}</y>")
                else:
                    logger.error(f"{self.session_name} | Error while checking TG group: <y>{chat.username}</y>")

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()
        except Exception as error:
            logger.error(f"{self.session_name} | Error while join tg channel: {error}")
            await asyncio.sleep(delay=3)

    async def get_mining_status(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://notpx.app/api/v1/mining/status')
            response.raise_for_status()
            response_json = await response.json()
            self.mining_data = response_json
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting mining status: {error}")
            await asyncio.sleep(delay=3)

    async def processing_tasks(self, http_client: aiohttp.ClientSession, completed_tasks: Any):
        try:
            logger.info(f"{self.session_name} | Searching for available tasks..")
            repaints_count = self.mining_data.get('repaintsTotal')
            for task in settings.TASKS:
                if task not in completed_tasks:
                    if task == 'leagueBonusSilver' and repaints_count < 28:
                        continue
                    if task == 'paint20pixels' and repaints_count < 20:
                        continue
                    task_link = task if 'x:' not in task else task.replace(':', '?name=')
                    response = await http_client.get(f'https://notpx.app/api/v1/mining/task/check/{task_link}')
                    response.raise_for_status()
                    response_json = await response.json()
                    status = response_json[task]
                    if status:
                        logger.success(
                            f"{self.session_name} | Task <lc>{task}</lc> completed!")
                    else:
                        logger.info(
                            f"{self.session_name} | Failed to complete task <lc>{task}</lc>")
                    await asyncio.sleep(delay=randint(3, 7))

            logger.info(f"{self.session_name} | Available tasks done")

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while processing tasks | Error: {e}")
            await asyncio.sleep(delay=3)

    async def paint_pixel(self, http_client: aiohttp.ClientSession):
        try:
            pixel_id = randint(1, 1000000)
            color = random.choice(settings.COLORS)
            payload = {
                "pixelId": pixel_id,
                "newColor": color
            }
            response = await http_client.post('https://notpx.app/api/v1/repaint/start', json=payload)
            response.raise_for_status()
            logger.success(f"{self.session_name} | Pixel <fg #ffbcd9>{pixel_id}</fg #ffbcd9> successfully painted | "
                           f"Color: <fg {color}>{color}</fg {color}>")
            await asyncio.sleep(delay=randint(5, 10))

        except Exception as error:
            logger.warning(f"{self.session_name} | Unknown error while painting")
            logger.error(f"{self.session_name} | Unknown error while painting: {error}")
            await asyncio.sleep(delay=3)

    async def upgrade_boost(self, http_client: aiohttp.ClientSession, boost_id:str):
        try:
            response = await http_client.get(f'https://notpx.app/api/v1/mining/boost/check/{boost_id}')
            if response.status == 500:
                logger.warning(f"{self.session_name} | Not enough money for upgrading <fg #6a329f>{boost_id}</fg #6a329f>")
                await asyncio.sleep(delay=randint(5, 10))
                return

            response.raise_for_status()
            logger.success(f"{self.session_name} | Boost <fg #6a329f>{boost_id}</fg #6a329f> successfully upgraded!")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when upgrading: {error}")
            await asyncio.sleep(delay=3)

    async def claim_mining_reward(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://notpx.app/api/v1/mining/claim')
            response.raise_for_status()
            response_json = await response.json()
            return response_json['claimed']
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting mining reward: {error}")
            await asyncio.sleep(delay=3)

    async def run(self, user_agent: str, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        headers["User-Agent"] = user_agent

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            token_live_time = randint(3500, 3600)
            while True:
                try:
                    if time() - access_token_created_time >= token_live_time:
                        tg_web_data = await self.get_tg_web_data(proxy=proxy)
                        if tg_web_data is None:
                            continue

                        http_client.headers["Authorization"] = f'initData {tg_web_data}'
                        user_info = await self.login(http_client=http_client)
                        league = user_info['league'] if user_info['league'] else 'None'
                        logger.info(f"{self.session_name} | Successful login | "
                                    f"Current league: <lc>{league}</lc>")
                        access_token_created_time = time()
                        token_live_time = randint(3500, 3600)
                        # sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])

                        mining_data = await self.get_mining_status(http_client)
                        balance = round(mining_data['userBalance'], 2)
                        logger.info(f"{self.session_name} | Balance: <e>{balance}</e>")

                        if settings.AUTO_TASK:
                            await self.processing_tasks(http_client=http_client, completed_tasks=mining_data['tasks'])
                            await asyncio.sleep(delay=(randint(5, 10)))

                        if settings.AUTO_UPGRADE:
                            boosts = mining_data['boosts']
                            energy = boosts['energyLimit']
                            paint = boosts['paintReward']
                            recharge = boosts['reChargeSpeed']
                            logger.info(
                                f"{self.session_name} | Boost Levels: Paint - <fg #fffc32>{paint} lvl</fg #fffc32> | "
                                f"Energy limit - <fg #fffc32>{energy} lvl</fg #fffc32> | "
                                f"Recharge speed - <fg #fffc32>{recharge} lvl</fg #fffc32>")

                            boosters = []
                            if settings.AUTO_UPGRADE_ENERGY and energy < settings.MAX_ENERGY_LEVEL:
                                boosters.append('energyLimit')
                            if settings.AUTO_UPGRADE_CHARGE and recharge < settings.MAX_CHARGE_LEVEL:
                                boosters.append('reChargeSpeed')
                            if settings.AUTO_UPGRADE_PAINT and paint < settings.MAX_PAINT_LEVEL:
                                boosters.append('paintReward')

                            random_boost = random.choice(boosters)
                            await self.upgrade_boost(http_client=http_client, boost_id=random_boost)
                            await asyncio.sleep(delay=randint(5, 10))

                        if settings.AUTO_MINING:
                            time_from_start = mining_data['fromStart']
                            max_mining_time = mining_data['maxMiningTime']
                            if time_from_start > max_mining_time - randint(0, 7200):
                                await self.claim_mining_reward(http_client=http_client)
                                await asyncio.sleep(delay=(randint(5, 10)))

                        if settings.AUTO_PAINT:
                            charges = mining_data['charges']
                            while charges > 0:
                                await asyncio.sleep(delay=randint(1, 10))
                                await self.paint_pixel(http_client=http_client)
                                charges -= 1

                    

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=randint(60, 120))
                finally:
                    sleep_time = randint(*settings.BIG_SLEEP)
                    logger.info(f"{self.session_name} | Sleep <y>{round(sleep_time / 60, 1)}</y> min")
                    await asyncio.sleep(delay=sleep_time)


async def run_tapper(tg_client: Client, user_agent: str, proxy: str | None):
    try:
        if not settings.ACCOUNTS_MOOD_SEQUENTIAL:
            _sleep = randint(*settings.LOGIN_SLEEP)
            logger.info(f"{tg_client.name} | Bot will start in {_sleep}s ...")
            await asyncio.sleep(_sleep)
            await Tapper(tg_client=tg_client).run(user_agent=user_agent, proxy=proxy)
        else:
            await Tapper(tg_client=tg_client).run(user_agent=user_agent, proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")


















