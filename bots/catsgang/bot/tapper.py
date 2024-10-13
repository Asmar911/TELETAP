import asyncio
import os
from datetime import datetime, timedelta
from time import time
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

from random import randint, choices, choice

from bot.youtube_tasks import YOUTUBE_TASKS

import json
import mimetypes
import os
import random

import aiofiles



class Tapper:
    def __init__(self, tg_client: Client):
        self.tg_client = tg_client
        self.session_name = f"{tg_client.name:<10}"
        self.start_param = ''
        self.name = ''

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

            peer = await self.tg_client.resolve_peer('catsgang_bot')
            link = choices([settings.REF_ID, "VcEZmxM20ef4jbRAn1ppe"], weights=[75, 25], k=1)[0]
            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                platform='androin',
                app=types.InputBotAppShortName(bot_id=peer, short_name="join"),
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

            me = await self.tg_client.get_me()
            self.name = me.first_name
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
            response = await http_client.get("https://api.catshouse.club/user",
                                             timeout=aiohttp.ClientTimeout(60))

            if response.status == 404:
                response = await http_client.post("https://api.catshouse.club/user/create",
                                                  params={"referral_code": self.start_param})
                response.raise_for_status()
                logger.success(f"{self.session_name} | User successfully registered!")
                await asyncio.sleep(delay=2)
                return await self.login(http_client)

            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as error:
            if retry < 5:
                logger.warning(f"{self.session_name} | Can't logging | Retry attempt: {retry}")
                await asyncio.sleep(delay=randint(5, 10))
                return await self.login(http_client, retry=retry+1)

            logger.error(f"{self.session_name} | Unknown error when logging: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://ipinfo.io/ip', timeout=aiohttp.ClientTimeout(20))
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

    async def get_all_tasks(self, http_client: aiohttp.ClientSession, groups: list[str], retry=0):
        try:
            tasks = []
            for group in groups:
                response = await http_client.get(f"https://api.catshouse.club/tasks/user?group={group}")
                response.raise_for_status()
                tasks_json = await response.json()
                tasks += tasks_json.get('tasks')
                await asyncio.sleep(delay=randint(1, 3))
            return tasks
        except Exception as error:
            if retry < 5:
                logger.warning(f"{self.session_name} | Can't getting tasks | Retry attempt: {retry}")
                await asyncio.sleep(delay=randint(5, 10))
                return await self.get_all_tasks(http_client, groups, retry=retry+1)

            logger.error(f"{self.session_name} | Unknown error when getting tasks: {error}")
            await asyncio.sleep(delay=3)

    def youtube_answer(self, title: str):
        tasks={
            "Boost Your Cats Earnings!": 'dildo',
            "Futures Trading PART 1": 'AIRNODE',
            "Futures Trading PART 2": 'WEI',
            "FREE Crypto": 'dip',
            "How To Make 10x On Crypto": 'ABSTRACT',
            "How To Make 10x On Crypto PART 2": 'AUCTION',
            "How To Make 10x On Crypto PART 3": 'AUDIT',
            "Productivity Tips!": 'BAKING',
            "How to Stay Productive": 'ALTCOIN',
            "Start From ZERO": 'ALPHA'
        }

        answer = tasks.get(title, None)
        return answer

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            tasks = await self.get_all_tasks(http_client, ['cats', 'bitget', 'kukoin', 'okx'])
            if tasks:
                for task in tasks:
                    if not task['completed'] and not task['isPending'] and task['type'] not in settings.DISABLED_TASKS:
                        if task['type'] == 'NICKNAME_CHANGE':
                            if '🐈‍⬛' in self.name:
                                result = await self.verify_task(http_client, task['id'], endpoint='check')
                                if result:
                                    logger.info(f"{self.session_name} | Removing 🐈 from nickname")
                                    name = self.name.split('🐈‍⬛')[0]
                                    await self.change_tg_nickname(name=name)
                            else:
                                logger.info(f"{self.session_name} | Performing <lc>{task['title']}</lc> task")
                                cat_name = f'{self.name}🐈‍⬛'
                                await self.change_tg_nickname(name=cat_name)
                                continue
                        elif task['type'] == 'SUBSCRIBE_TO_CHANNEL' and settings.JOIN_TG_CHANNELS:
                            url = task['params']['channelUrl']
                            logger.info(f"{self.session_name} | Performing TG subscription to <lc>{url}</lc>")
                            await self.join_tg_channel(url)
                            result = await self.verify_task(http_client, task['id'], endpoint='check')
                        elif task['type'] == 'YOUTUBE_WATCH':
                            logger.info(f'{self.session_name} | Performing Youtube <y>{task["title"]}</y>')
                            answer = self.youtube_answer(task['title'])
                            if answer:
                                endpoint = f'complete?answer={answer}'
                                await asyncio.sleep(delay=randint(30, 60))
                                result = await self.verify_task(http_client, task['id'], endpoint=endpoint)
                            else:
                                logger.warning(f'{self.session_name} | Answer for task <y>{task["title"]}</y> not found')
                                continue
                        else:
                            logger.info(f"{self.session_name} | Performing <lc>{task['title']}</lc> task")
                            result = await self.verify_task(http_client, task['id'], endpoint='complete')

                        if result:
                            logger.success(f"{self.session_name} | Task <lc>{task['title']}</lc> completed! |"
                                           f" Reward: <e>+{task['rewardPoints']}</e> CATS")
                        else:
                            logger.info(f"{self.session_name} | Task <lc>{task['title']}</lc> not completed")

                        await asyncio.sleep(delay=randint(5, 10))

                    elif task['isPending']:
                        logger.info(f"{self.session_name} | Task <lc>{task['title']}</lc> is pending")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def verify_task(self, http_client: aiohttp.ClientSession, task_id: str, endpoint: str, retry=0):
        try:
            response = await http_client.post(f'https://api.catshouse.club/tasks'
                                              f'/{task_id}/{endpoint}', json={}, timeout=aiohttp.ClientTimeout(60))
            response.raise_for_status()
            response_json = await response.json()
            status = response_json.get('success', False) or response_json.get('completed', False)
            return status

        except Exception as e:
            if retry < 5:
                logger.warning(f"{self.session_name} | Can't verify task | Retry attempt: {retry}")
                await asyncio.sleep(delay=randint(5, 10))
                return await self.verify_task(http_client, task_id, endpoint, retry=retry+1)

            logger.error(f"{self.session_name} | Unknown error while verifying task {task_id} | Error: {e}")
            await asyncio.sleep(delay=3)

    async def get_avatar_info(self, http_client: aiohttp.ClientSession, retry=0):
        try:
            response = await http_client.get('https://api.catshouse.club/user/avatar')
            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as e:
            if retry < 5:
                logger.warning(f"{self.session_name} | Can't getting avatar info | Retry attempt: {retry}")
                await asyncio.sleep(delay=randint(5, 10))
                return await self.get_avatar_info(http_client, retry=retry+1)

            logger.error(f"{self.session_name} | Unknown error while getting avatar info | Error: {e}")
            await asyncio.sleep(delay=3)

    async def check_available(self, http_client: aiohttp.ClientSession, retry=0):
        try:
            response = await http_client.get('https://api.catshouse.club/exchange-claim/check-available')
            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as e:
            if retry < 5:
                logger.warning(f"{self.session_name} | Can't getting airdrop data | Retry attempt: {retry}")
                await asyncio.sleep(delay=randint(5, 10))
                return await self.check_available(http_client, retry=retry+1)

            logger.error(f"{self.session_name} | Unknown error while getting airdrop data | Error: {e}")
            await asyncio.sleep(delay=3)

    def generate_random_string(self, length=8):
        characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        random_string = ''
        for _ in range(length):
            random_index = int((len(characters) * int.from_bytes(os.urandom(1), 'big')) / 256)
            random_string += characters[random_index]
        return random_string
    
    async def get_random_cat_image(self):
        images = [f for f in os.listdir(settings.CATS_PATH) if f.lower().endswith(('.png', '.jpeg', '.jpg'))]
        if not images:
            logger.warning(f"Please, add cats images in '{settings.CATS_PATH}' folder")
            return None

        image = random.choice(images)
        logger.info(f"{self.session_name} | Selected image: <y>{image}</y>")
        image_path = os.path.join(settings.CATS_PATH, image)
        mime_type = mimetypes.guess_type(image_path)

        async with aiofiles.open(image_path, 'r+b') as file:
            data = await file.read()

        image_data = (f'Content-Disposition: form-data; name="photo"; filename="{image}"\r\n'
                    f'Content-Type: {mime_type}\r\n\r\n').encode('utf-8')
        image_data += data
        return image_data

    async def processing_avatar_task(self, http_client: aiohttp.ClientSession):
        try:
            cat_image = await self.get_random_cat_image()
            hash_id = self.generate_random_string(length=16)
            http_client.headers['Content-Type'] = f'multipart/form-data; boundary=----WebKitFormBoundary{hash_id}'
            data = (f'------WebKitFormBoundary{hash_id}\r\n'.encode('utf-8') + cat_image +
                    f'\r\n------WebKitFormBoundary{hash_id}--\r\n'.encode('utf-8'))
            response = await http_client.post('https://api.catshouse.club/user/avatar/upgrade',
                                              data=data)
            http_client.headers['Content-Type'] = headers['Content-Type']
            response.raise_for_status()
            response_json = await response.json()
            logger.info(
                f"{self.session_name} | Avatar task completed! | Reward: <e>+{response_json['rewards']}</e> CATS")
            return response_json

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while processing avatar task | Error: {e}")
            await asyncio.sleep(delay=3)

    async def change_tg_nickname(self, name: str):
        try:
            if not self.tg_client.is_connected:
                await self.tg_client.connect()

            await self.tg_client.update_profile(first_name=name)
            logger.info(f"{self.session_name} | Nickname changed to <lc>{name}</lc>")
        except Exception as error:
            logger.error(
                f"<light-yellow>{self.session_name}</light-yellow> | Error updating profile nickname: {error}")
        finally:
            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

    async def run(self, user_agent: str, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        headers["User-Agent"] = user_agent

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn, trust_env=True) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            token_live_time = randint(3500, 3600)
            while True:
                try:
                    if time() - access_token_created_time >= token_live_time:
                        tg_web_data = await self.get_tg_web_data(proxy=proxy)
                        if tg_web_data is None:
                            continue

                        http_client.headers["Authorization"] = "tma " + tg_web_data
                        user_info = await self.login(http_client=http_client)
                        if user_info is None:
                            token_live_time = 0
                            await asyncio.sleep(randint(1000, 1800))
                            continue

                        access_token_created_time = time()
                        token_live_time = randint(3500, 3600)

                        balance = user_info['totalRewards']
                        logger.info(f"{self.session_name} | Balance: <e>{balance}</e> CATS")
                        result = await self.check_available(http_client=http_client)
                        if result:
                            logger.info(f'{self.session_name} '
                                        f'| Has free pass: <lc>{result.get("hasFreePass")}</lc> '
                                        f'| Has OG pass: <lc>{result.get("hasOgPass")}</lc> '
                                        f'| Has transaction: <lc>{result.get("hasTransaction")}</lc> '
                                        f'| Is available for Airdrop: <e>{result.get("isAvailable")}</e>')

                        if settings.AUTO_TASK:
                            await asyncio.sleep(delay=randint(5, 10))
                            await self.processing_tasks(http_client=http_client)

                    if settings.AVATAR_TASK:
                        avatar_info = await self.get_avatar_info(http_client=http_client)
                        og_pass = user_info.get('hasOgPass', False)
                        logger.info(f"{self.session_name} | OG Pass: <y>{og_pass}</y>")
                        if avatar_info:
                            attempt_time = None
                            if avatar_info['attemptTime'] is not None:
                                attempt_time = avatar_info['attemptTime']
                                parsed_time = datetime.strptime(attempt_time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
                                delta_time = datetime.utcnow().timestamp() - parsed_time
                                next_attempt_time = delta_time - timedelta(hours=24).total_seconds()
                                max_attempts = 3 if og_pass else 1
                                used_attempts = avatar_info['attemptsUsed'] if next_attempt_time < 0 else 0
                            if attempt_time is None or used_attempts < max_attempts:
                                for attempt in range(max_attempts - used_attempts):
                                    await asyncio.sleep(delay=randint(5, 10))
                                    await self.processing_avatar_task(http_client=http_client)

                            # elif next_attempt_time < 0:
                            #     print(f"next_attempt_time: {next_attempt_time}")
                            #     sleep_time = min(randint(*settings.BIG_SLEEP), abs(int(next_attempt_time)))
                            #     print(f"sleep_time: {sleep_time}")

                    

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=randint(60, 120))

                finally:
                    SLEEP = randint(*settings.BIG_SLEEP)
                    logger.info(f"{self.session_name} | Big Sleep <y>{round(SLEEP / 60, 1)}</y> min")
                    await asyncio.sleep(delay=SLEEP)





async def run_tapper(tg_client: Client, user_agent: str, proxy: str | None):
    try:
        if not settings.ACCOUNTS_MOOD_SEQUENTIAL:
            _sleep = randint(*settings.LOGIN_SLEEP)
            logger.info(f"{tg_client.name:<10} | Bot will start in {_sleep}s ...")
            await asyncio.sleep(_sleep)
            await Tapper(tg_client=tg_client).run(user_agent=user_agent, proxy=proxy)
        else:
            await Tapper(tg_client=tg_client).run(user_agent=user_agent, proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")


















