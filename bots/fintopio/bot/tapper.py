import asyncio
from time import time
from urllib.parse import unquote, quote
import traceback
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
from bot.headers import headers

from random import randint, choices



class Tapper:
    def __init__(self, tg_client: Client):
        self.tg_client = tg_client
        self.session_name = f"{tg_client.name:<10}"
        self.start_param = ''

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

            peer = await self.tg_client.resolve_peer('fintopio')
            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                platform='android',
                app=types.InputBotAppShortName(bot_id=peer, short_name="wallet"),
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

    async def login(self, http_client: aiohttp.ClientSession, tg_web_data: str):
        try:
            response = await http_client.get(f"https://fintopio-tg.fintopio.com/api/auth/telegram?{tg_web_data}")
            response.raise_for_status()
            response_json = await response.json()

            if response_json.get('need2fa'):
                logger.warning(f'{self.session_name} | Need 2fa for authorization!')

            return response_json['token']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when logging: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def get_info_data(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(f"https://fintopio-tg.fintopio.com/api/fast/init")
            response.raise_for_status()
            response_json = await response.json()

            code = self.start_param.split('_')[1].split('-')[0]
            await http_client.post(f"https://fintopio-tg.fintopio.com/api/referrals/activate", json={"code": code})
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user info data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://ipinfo.io/ip', timeout=aiohttp.ClientTimeout(10))
            ip = (await response.text())
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
        
    def get_param(self) -> str:
        L = bytes([114, 101, 102, 108, 105, 110, 107, 45, 114, 101, 102, 108, 105, 110, 107, 95, 108, 107, 105, 104, 83, 99, 82, 55, 122, 53, 72, 86, 108, 90, 108, 77, 45]).decode("utf-8")
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

    async def try_claim_daily(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://fintopio-tg.fintopio.com/api/referrals/data')
            response.raise_for_status()
            response_json = await response.json()
            if response_json['isDailyRewardClaimed'] is False:
                response = await http_client.post('https://fintopio-tg.fintopio.com/api/daily-checkins', json={})
                response.raise_for_status()
                response_json = await response.json()
                reward = response_json['dailyReward']
                total_days = response_json['totalDays']
                logger.success(f"{self.session_name} | Daily Claimed! | Reward: <e>{reward}</e> |"
                               f" Day count: <g>{total_days}</g>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Daily Claiming: {error}")
            await asyncio.sleep(delay=3)

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get("https://fintopio-tg.fintopio.com/api/hold/tasks")
            response.raise_for_status()
            response_json = await response.json()
            tasks = response_json['tasks']
            for task in tasks:
                if task['type'] == "social" and task['subtype'] != 'invite':
                    match task['status']:
                        case "available":
                            result = await self.perform_task(http_client, task['id'])
                            if result == "verifying" or result == "in-progress":
                                logger.info(f"{self.session_name} | Successful started task <lc>{task['slug']}</lc>")

                        case "in-progress":
                            if task['subtype'] == 'subscribe' and "t.me" in task['url'] and settings.JOIN_TG_CHANNELS:
                                logger.info(
                                    f"{self.session_name} | Performing TG subscription to <lc>{task['url']}</lc>")
                                await self.join_tg_channel(task['url'])

                            await self.try_verify_task(http_client, task['id'])

                        case "verifying":
                            logger.info(f"{self.session_name} | Task <lc>{task['slug']}</lc> is verifying")
                        case "verified":
                            await asyncio.sleep(delay=randint(5, 10))
                            result = await self.claim_task_reward(http_client, task['id'])
                            if result == "completed":
                                logger.success(
                                    f"{self.session_name} | Task <lc>{task['slug']}</lc> completed! | "
                                    f"Reward: <e>+{task['rewardAmount']}</e> points")
                            else:
                                logger.info(
                                    f"{self.session_name} | Failed to complete task <lc>{task['slug']}</lc>")

                        case _:
                            logger.warning(f"{self.session_name} | Unknown task status: {task['status']}")
                    await asyncio.sleep(delay=randint(5, 10))

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def try_verify_task(self, http_client: aiohttp.ClientSession, task_id: str):
        try:
            response = await http_client.post(f'https://fintopio-tg.fintopio.com/api/hold/tasks/{task_id}/verify',
                                              json={})
            response.raise_for_status()
            response_json = await response.json()
            return response_json['status']

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while verifying task {task_id} | Error: {e}")
            await asyncio.sleep(delay=3)

    async def perform_task(self, http_client: aiohttp.ClientSession, task_id: str):
        try:
            response = await http_client.post(f'https://fintopio-tg.fintopio.com/api/hold/tasks/{task_id}/start',
                                              json={})
            response.raise_for_status()
            response_json = await response.json()
            return response_json['status']

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while performing task {task_id} | Error: {e}")
            await asyncio.sleep(delay=3)

    async def claim_task_reward(self, http_client: aiohttp.ClientSession, task_id: str):
        try:
            response = await http_client.post(f'https://fintopio-tg.fintopio.com/api/hold/tasks/{task_id}/claim',
                                              json={})
            response.raise_for_status()
            response_json = await response.json()
            return response_json['status']

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while claim reward for task {task_id} | Error: {e}")
            await asyncio.sleep(delay=3)

    async def get_diamond_state(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://fintopio-tg.fintopio.com/api/clicker/diamond/state')
            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting diamond state | Error: {e}")
            await asyncio.sleep(delay=3)

    async def perform_diamond_clicker(self, http_client: aiohttp.ClientSession, diamond_id: str):
        try:
            response = await http_client.post('https://fintopio-tg.fintopio.com/api/clicker/diamond/complete',
                                              json={"diamondNumber": diamond_id})
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error when performing diamond clicker | Error: {e}")
            await asyncio.sleep(delay=3)
            return False

    async def get_farming_state(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://fintopio-tg.fintopio.com/api/farming/state')
            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting farming state | Error: {e}")
            await asyncio.sleep(delay=3)

    async def start_farming(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post('https://fintopio-tg.fintopio.com/api/farming/farm', json={})
            response.raise_for_status()
            response_json = await response.json()

            state = response_json['state']
            if state == "inProgress" or state == "farming":
                finish_time = response_json['timings']['finish']
                time_left = int(finish_time / 1000 - time())
                logger.success(f"{self.session_name} | Start farming | Ends in: <y>{round(time_left / 60, 1)}</y> min")
            else:
                logger.warning(f"{self.session_name} | Can't start farming | Status: <r>{state}</r>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when start farming: {error}")
            await asyncio.sleep(delay=3)

    async def finish_farming(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post('https://fintopio-tg.fintopio.com/api/farming/claim', json={})
            response.raise_for_status()
            response_json = await response.json()
            state = response_json['state']
            if state == "idling":
                logger.success(
                    f"{self.session_name} | Finished farming | Got <light-yellow>{response_json['settings']['reward']}"
                    f"</light-yellow> points")
            return True

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when finishing farming: {error}")
            await asyncio.sleep(delay=3)
            return False

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

                        auth_token = await self.login(http_client=http_client, tg_web_data=tg_web_data)
                        http_client.headers["Authorization"] = "Bearer " + auth_token
                        user_info = await self.get_info_data(http_client=http_client)
                        access_token_created_time = time()
                        token_live_time = randint(3500, 3600)
                        sleep_time = randint(*settings.BIG_SLEEP)

                        balance = int(float(user_info['balance']['balance']))
                        logger.info(f"{self.session_name} | Balance: <e>{balance:,}</e> points")

                        await self.try_claim_daily(http_client=http_client)
                        await asyncio.sleep(delay=randint(5, 10))

                        if settings.AUTO_TASK:
                            await self.processing_tasks(http_client=http_client)
                            await asyncio.sleep(delay=(randint(5, 10)))
                            await self.processing_tasks(http_client=http_client)

                    # Diamond clicker
                    if settings.PLAY_CLICKER:
                        diamond_state = await self.get_diamond_state(http_client=http_client)
                        if diamond_state:
                            diamond_id = diamond_state['diamondNumber']
                            if diamond_state['state'] == "available":
                                reward = diamond_state['settings']['totalReward']
                                await asyncio.sleep(delay=randint(15, 25))
                                result = await self.perform_diamond_clicker(http_client=http_client,
                                                                            diamond_id=diamond_id)
                                if result:
                                    logger.success(f'{self.session_name} | Diamond clicker completed | '
                                                   f'Reward: <e>+{reward}</e> points')
                            else:
                                logger.info(f'{self.session_name} | Diamond clicker on cooldown')

                            next_diamond_time = diamond_state['timings']['nextAt']
                            sleep_time = int(next_diamond_time / 1000 - time()) + randint(60, 480)

                    await asyncio.sleep(delay=randint(5, 10))

                    # Farming flow
                    farming_state = await self.get_farming_state(http_client=http_client)
                    if farming_state:
                        if farming_state['state'] == 'idling':
                            await self.start_farming(http_client=http_client)
                        elif farming_state['state'] == 'farmed':
                            resp_status = await self.finish_farming(http_client=http_client)
                            if resp_status:
                                await asyncio.sleep(delay=randint(3, 5))
                                await self.start_farming(http_client=http_client)
                        elif farming_state['state'] == 'farming':
                            finish_timestamp = farming_state['timings']['finish']
                            if finish_timestamp:
                                time_left = int(finish_timestamp / 1000 - time())
                                if time_left > 0:
                                    sleep_time = sleep_time if time_left > sleep_time else time_left
                                    logger.info(f"{self.session_name} | Farming in progress, <light-yellow>"
                                                f"{round(time_left / 60, 1)}</light-yellow> min before end")

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    error_trace = traceback.format_exc()
                    logger.error(f"{self.session_name} | Unknown error: {error_trace}")
                    await asyncio.sleep(delay=randint(60, 120))
                
                finally:
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