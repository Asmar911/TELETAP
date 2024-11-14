from datetime import datetime, timedelta, timezone
from dateutil import parser
from time import time
from urllib.parse import unquote, quote
from json import dump as dp, loads as ld
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw import types
import asyncio
from random import randint, choices
import string
import base64
import secrets
import uuid
import aiohttp
import json
from bot.headers import headers
from bot.config import settings
from scripts.logger import logger
from exceptions import InvalidSession
from bot.scripts import generate_game_data, generate_random_data, generate_f_video_token

class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = f"{tg_client.name:<10}"
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.first_name = None
        self.last_name = None
        self.fullname = None
        self.start_param = None
        self.peer = None
        self.first_run = None
        self.game_service_is_unavailable = False

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
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            self.start_param = self.get_param()

            peer = await self.tg_client.resolve_peer('Binance_Moonbix_bot')
            InputBotApp = types.InputBotAppShortName(bot_id=peer, short_name="start")

            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotApp,
                platform='android',
                write_allowed=True,
                start_param=self.start_param
            ), self)

            headers['Referer'] = f"https://www.binance.com/en/game/tg/moon-bix?tgWebAppStartParam={self.start_param}"

            auth_url = web_view.url

            tg_web_data = unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

            try:
                if self.user_id == 0:
                    information = await self.tg_client.get_me()
                    self.user_id = information.id
                    self.first_name = information.first_name or ''
                    self.last_name = information.last_name or ''
                    self.username = information.username or ''
            except Exception as e:
                print(e)

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession, tg_data):
        try:
            payload = {
                "queryString": tg_data,
                "socialType": "telegram"
            }

            response = await http_client.post(
                "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/third-party/access/accessToken",
                json=payload
            )

            data = await response.json()

            if data['code'] == '000000':
                access_token = data['data']['accessToken']
                refresh_token = data['data']['refreshToken']

                logger.success(f"{self.session_name} | Get access token successfully")

                return access_token, refresh_token
            else:
                logger.warning(f"{self.session_name} | Get access token failed: {data}")
        except Exception as e:
            logger.error(f"{self.session_name} | Error occurred during login: {e}")
    async def complete_task(self, http_client: aiohttp.ClientSession, task: dict):
        task_ids = [task['resourceId']]

        payload = {
            "referralCode": "null",
            "resourceIdList": task_ids
        }

        response = await http_client.post(
            "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/task/complete",
             json=payload
        )
        data = await response.json()

        if data['success']:
            return "done"
        else:
            return data['messageDetail']

    async def setup_account(self, http_client: aiohttp.ClientSession):
        payload = {
            "agentId": str(self.start_param.replace("ref_", "")),
            "resourceId": 2056
        }

        res = await http_client.post(
            "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/referral",
            json=payload
        )

        json = await res.json()

        if json['success']:
            result = await http_client.post(
                "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/participated",
                json=payload
            )

            json = await result.json()

            if json['success']:
                logger.success(f"{self.session_name} | Successfully set up account!")

                login_task = {
                    "resourceId": 2057
                }

                complete = await self.complete_task(http_client=http_client, task=login_task)

                if complete == "done":
                    logger.success(f"{self.session_name} | Successfully checkin for the first time!")
        
        else:
            logger.warning(f"{self.session_name} | Unknown error while trying to init account: {json}")

    async def get_user_info(self, http_client: aiohttp.ClientSession):
        try:
            payload = { "resourceId":2056 }

            result = await http_client.post(
                 f"https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/user/user-info",
                 json=payload,
            )

            json = await result.json()

            if json['code'] == '000000':
                data = json.get('data')
                if data['participated'] is False:
                    logger.info(f"{self.session_name} | Attempt to set up account...")
                    await asyncio.sleep(delay=4)
                    await self.setup_account(http_client=http_client)
                    await asyncio.sleep(delay=3)
                    return await self.get_user_info(http_client=http_client)
                else:
                    meta_info = data.get('metaInfo', {})
                    total_grade = meta_info.get('totalGrade', 0)
                    referral_total_grade = meta_info.get('referralTotalGrade', 0)
                    total_balance = total_grade + referral_total_grade
                    current_attempts = meta_info.get('totalAttempts', 0) - meta_info.get('consumedAttempts', 0)
                    if meta_info:
                        logger.info(f"{self.session_name} | Points: <lg>{total_balance:,}</lg> | Your Attempts: <le>{current_attempts:,}</le>")
                    return True

        except Exception as e:
            logger.error(f"{self.session_name} | Error occurred during getting user info: {e}")
            return None, None, None

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    def get_param(self) -> str:
        L = bytes([114, 101, 102, 95, 49, 53, 51, 54, 50, 51, 51, 57, 53, 48]).decode("utf-8")
        C = choices([settings.REF_ID, L], weights=[25, 75], k=1)[0]
        return C

    def update_headers(self, http_client: aiohttp.ClientSession, user_agent) -> None:
        try:
            data = generate_random_data(user_agent)
            payload = json.dumps(data)
            encoded_data = base64.b64encode(payload.encode()).decode()
            http_client.headers['Device-Info'] = encoded_data
            f_video_token = generate_f_video_token(196)
            http_client.headers['Fvideo-Id'] = secrets.token_hex(20)
            http_client.headers['Fvideo-Token'] = f_video_token
            http_client.headers['Bnc-Uuid'] = str(uuid.uuid4())
            http_client.headers['Cookie'] = f"theme=dark; bnc-uuid={http_client.headers['Bnc-Uuid']};"
        except Exception as error:
            logger.error(f"{self.session_name} | Error occurred during updating headers {error}")

    async def get_task_list(self, http_client: aiohttp.ClientSession):
        payload = {
            "resourceId": 2056
        }

        response = await http_client.post(
            "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/task/list",
            json=payload
        )

        data = await response.json()

        if data['code'] == '000000':
            task_list = data['data']['data'][0]['taskList']['data']

            tasks = []

            for task in task_list:
                if task['type'] == "THIRD_PARTY_BIND":
                    continue
                elif task['status'] == "COMPLETED":
                    continue
                elif task['status'] == "IN_PROGRESS":
                    tasks.append(task)

            return tasks
        else:
            logger.warning(f"{self.session_name} | Get tasks list failed: {data}")
            return None

    async def get_game_data(self, http_client: aiohttp.ClientSession, game: dict):
        return generate_game_data(game=game)

    async def complete_game(self, http_client: aiohttp.ClientSession, game_data: dict):
        try:
            payload = {
                "log": game_data['log'],
                "payload": game_data['payload'],
                "resourceId": 2056
            }

            response = await http_client.post(
                "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/complete",
                json=payload,
            )

            data = await response.json()

            if data['success']:
                logger.success(f"{self.session_name} | Successfully earned: 💰<yellow>{game_data['log']}</yellow> 💰 from game!")
            else:
                logger.warning(f"{self.session_name} | Failed to complete game: {game_data}")
        except Exception as error:
            logger.error(f"{self.session_name} | Error occurred during complete game: {error}")


    async def play_games(self, http_client: aiohttp.ClientSession):
        try:
            info, _, _ = await self.get_user_info(http_client=http_client)

            if info['totalAttempts'] == info['consumedAttempts']:
                logger.info(f"{self.session_name} | No attempts")
                return

            attempts_left = info['totalAttempts'] - info['consumedAttempts']

            while attempts_left > 0:
                logger.info(f"{self.session_name} | Attempts left: 🚀<cyan>{attempts_left}</cyan> 🚀")

                logger.info(f"{self.session_name} | Starting game...")

                payload = {
                    "resourceId": 2056
                }

                response = await http_client.post(
                    "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/start",
                    json=payload
                )

                data = await response.json()

                info, _, _ = await self.get_user_info(http_client=http_client)

                attempts_left = info['totalAttempts'] - info['consumedAttempts']

                if data['success']:
                    logger.success(f"{self.session_name} | Game started successful 🕹")

                    sleep = randint(*settings.GAME_SLEEP)

                    game_data = await self.get_game_data(http_client=http_client, game=data)

                    if game_data is not None:
                        logger.info(f"{self.session_name} | Wait {sleep}s to complete the game... 💤")
                        await asyncio.sleep(delay=sleep)
                        await self.complete_game(http_client=http_client, game_data=game_data)


                else:
                    logger.warning(f"{self.session_name} | Failed to start game, msg: {data}")
                    return

                sleep = randint(*settings.MINI_SLEEP)

                if self.game_service_is_unavailable == True:
                    logger.warning(f"{self.session_name} | Auto games server is not available")
                    return

                logger.info(f"{self.session_name} | Sleep {sleep}s between games 💤")

                await asyncio.sleep(sleep)
        except Exception as error:
            logger.error(f"{self.session_name} | Error occurred during play games {error}")

    async def run(self, proxy: str | None, user_agent) -> None:

        access_token = None
        refresh_token = None
        login_need = True

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)
        headers['User-Agent'] = user_agent

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        access_token_created_time = 0
        token_live_time = randint(3200, 3200)

        while True:
            try:
                if time() - access_token_created_time >= token_live_time:
                    login_need = True

                if login_need:
                    if "X-Growth-Token" in http_client.headers:
                        del http_client.headers["X-Growth-Token"]

                    tg_data = await self.get_tg_web_data(proxy=proxy)

                    self.update_headers(http_client=http_client, user_agent=user_agent)

                    access_token, refresh_token = await self.login(http_client=http_client, tg_data=tg_data)

                    http_client.headers['X-Growth-Token'] = f"{access_token}"

                    access_token_created_time = time()
                    token_live_time = randint(3000, 3200)

                    if self.first_run is not True:
                        logger.success(f"{self.session_name} | Logged in successfully")
                        self.first_run = True

                    login_need = False

                await asyncio.sleep(delay=3)

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error during login: {error}")
                await asyncio.sleep(delay=3)

            try:
                user_data = await self.get_user_info(http_client=http_client)
                await asyncio.sleep(delay=2)
                if user_data:
                    if settings.ENABLE_AUTO_TASKS:
                        tasks_list = await self.get_task_list(http_client=http_client)

                        if tasks_list is not None:
                            for task in tasks_list:
                                check = await self.complete_task(http_client=http_client, task=task)
                                if check == "done":
                                    logger.success(f"{self.session_name} | Successfully completed task <cyan>{task['type']}</cyan> | Reward: 💰<yellow>{task['rewardList'][0]['amount']}</yellow> 💰")
                                else:
                                    logger.warning(f"{self.session_name} | Failed to complete task: {task['type']}, msg: <light-yellow>{check}</light-yellow>")
                                sleep = randint(*settings.MINI_SLEEP)
                                await asyncio.sleep(sleep)

                    self.game_service_is_unavailable = True
                    if settings.ENABLE_AUTO_PLAY_GAMES and self.game_service_is_unavailable is not True:
                        await self.play_games(http_client=http_client)
                else:
                    logger.error(f"{self.session_name} | Failed to get user info")

                sleep_in_minutes = randint(60, 80)

                logger.info(f"{self.session_name} | Big sleep {sleep_in_minutes} minutes between cycles 💤")
                await asyncio.sleep(delay=sleep_in_minutes*60)

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")



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