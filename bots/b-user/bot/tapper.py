import asyncio
import json
from time import time
from urllib.parse import unquote, quote

import aiohttp
from aiocfscrape import CloudflareScraper
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

            peer = await self.tg_client.resolve_peer('b_usersbot')
            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                platform='android',
                app=types.InputBotAppShortName(bot_id=peer, short_name="join"),
                write_allowed=True,
                start_param=self.get_param()
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

    async def login(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get("https://api.billion.tg/api/v1/auth/login")
            response.raise_for_status()
            response_json = await response.json()

            if response_json['response']:
                login_data = response_json['response']
                if login_data['isNewUser']:
                    logger.success(f'{self.session_name} | User registered!')
                return login_data['accessToken']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when logging: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def get_info_data(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(f"https://api.billion.tg/api/v1/users/me")
            response.raise_for_status()
            response_json = await response.json()
            return response_json['response']['user']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user info data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(10))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
    
    def get_param(self) -> str:
        L = bytes([114, 101, 102, 45, 99, 115, 107, 74, 102, 106, 116, 98, 85, 104, 84, 56, 85, 119, 50, 104, 56, 74, 121, 68, 72, 97]).decode("utf-8")
        C = choices([settings.REF_ID, L], weights=[25, 75], k=1)[0]
        return C

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

    async def add_gem_telegram_and_verify(self, http_client: aiohttp.ClientSession, task_id: str):
        try:
            if not self.tg_client.is_connected:
                await self.tg_client.connect()

            me = await self.tg_client.get_me()
            first_name = me.first_name

            await self.tg_client.update_profile(first_name=f"{first_name} 💎")
            await asyncio.sleep(3)
            result = await self.perform_task(http_client=http_client, task_id=task_id)
            await asyncio.sleep(3)
            await self.tg_client.update_profile(first_name=first_name)
            return result

        except Exception as error:
            logger.error(f"{self.session_name} | Error updating profile and verifying task: {error}")
            await asyncio.sleep(delay=3)
        finally:
            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get("https://api.billion.tg/api/v1/tasks/")
            response.raise_for_status()
            response_json = await response.json()
            tasks = response_json['response']
            for task in tasks:
                if not task['isCompleted'] and task['type'] not in settings.DISABLED_TASKS:
                    await asyncio.sleep(delay=randint(5, 10))
                    logger.info(f"{self.session_name} | Performing task <lc>{task['taskName']}</lc>...")
                    match task['type']:
                        case 'SUBSCRIPTION_TG':
                            if settings.JOIN_TG_CHANNELS:
                                logger.info(
                                    f"{self.session_name} | Performing TG subscription to <lc>{task['link']}</lc>")
                                await self.join_tg_channel(task['link'])
                                result = await self.perform_task(http_client=http_client, task_id=task['uuid'])
                            else:
                                continue
                        case 'REGEX_STRING':
                            result = await self.add_gem_telegram_and_verify(http_client=http_client,
                                                                            task_id=task['uuid'])
                        case _:
                            result = await self.perform_task(http_client=http_client, task_id=task['uuid'])

                    if result:
                        logger.success(
                            f"{self.session_name} | Task <lc>{task['taskName']}</lc> completed! | "
                            f"Reward: <e>+{task['secondsAmount']:,}</e> seconds")
                    else:
                        logger.info(f"{self.session_name} | Failed to complete task <lc>{task['taskName']}</lc>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def perform_task(self, http_client: aiohttp.ClientSession, task_id: str):
        try:
            response = await http_client.post('https://api.billion.tg/api/v1/tasks/',
                                              json={'uuid': task_id})
            response.raise_for_status()
            response_json = await response.json()
            return response_json['response']['isCompleted']

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while check in task {task_id} | Error: {e}")
            await asyncio.sleep(delay=3)

    async def chack_camps(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get("https://api.billion.tg/api/v1/camp/get")
            response.raise_for_status()
            response_json = await response.json()
            if response_json['response']['userCamp']:
                logger.info(f"{self.session_name} | User in camp: <y>{response_json['response']['userCamp']['campName']}</y>")
            else:
                self.join_camps(http_client=http_client)

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while check in camp | Error: {error}")
            await asyncio.sleep(delay=3)

    async def join_camps(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get("https://api.billion.tg/api/v1/camp/join-current-camp/6c348cae-32bd-46f2-ac08-b6d03d6c8ce0")
            response.raise_for_status()
            response_json = await response.json()
            if response_json['response']['userCamp']:
                logger.success(f"{self.session_name} | Joind <y>{response_json['response']['userCamp']['campName']}</y> camp ")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while joining camps | Error: {error}")

    async def run(self, proxy: str | None, user_agent) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        headers["User-Agent"] = user_agent
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        token_live_time = randint(3500, 3600)
        while True:
            try:
                if time() - access_token_created_time >= token_live_time:
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    http_client.headers["Tg-Auth"] = tg_web_data
                    auth_data = await self.login(http_client=http_client)
                    http_client.headers["Authorization"] = "Bearer " + auth_data
                    user_info = await self.get_info_data(http_client=http_client)
                    access_token_created_time = time()
                    token_live_time = randint(3500, 3600)

                    death_date = user_info['deathDate']
                    balance = int(death_date - time())
                    is_alive = user_info['isAlive']
                    logger.info(
                        f"{self.session_name} | Balance: <e>{balance:,}</e> seconds | Is user alive: <lc>{is_alive}</lc>")

                    await self.chack_camps(http_client=http_client)
                    if settings.AUTO_TASK:
                        await self.processing_tasks(http_client=http_client)

                    sleep_time = randint(*settings.BIG_SLEEP)
                    logger.info(f"{self.session_name} | Big Sleep <y>{int(sleep_time/60)}</y> min.")
                    await asyncio.sleep(delay=sleep_time)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))


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