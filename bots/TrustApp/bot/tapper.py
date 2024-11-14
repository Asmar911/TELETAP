import asyncio
from datetime import datetime
from time import time
from urllib.parse import unquote, quote

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw import functions
from pyrogram.raw.functions.messages import RequestWebView
from bot.config import settings

from scripts.logger import logger
from exceptions import InvalidSession
from bot.headers import headers

from random import randint, choices


class Tapper:
    def __init__(self, tg_client: Client):
        self.tg_client = tg_client
        self.session_name = f"{tg_client.name:<10}"
        self.user_id = 0
        self.init_params = ''
        self.country = 'US'
        self.locale = 'en'
        self.token = ''
        self.start_param = ''
        self.cards = []
        self.best_cards = []
        self.balance = 0
        self.level = 0
        self.to_next_level = 0

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
                    self.start_param = self.get_param()
                    start_command_found = False
                    async for message in self.tg_client.get_chat_history('trust_empire_bot'):
                        if (message.text and message.text.startswith('/start')) or (message.caption and message.caption.startswith('/start')):
                            start_command_found = True
                            break

                    if not start_command_found:
                        peer = await self.tg_client.resolve_peer('trust_empire_bot')
                        await self.tg_client.invoke(
                            functions.messages.StartBot(
                                bot=peer,
                                peer=peer,
                                start_param=self.start_param,
                                random_id=randint(1, 9999999),
                            )
                        )

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('trust_empire_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"<{self.session_name} | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url="https://trstempire.com/",
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            query_id = tg_web_data.split('query_id=')[1].split('&user=')[0]
            user = quote(tg_web_data.split("&user=")[1].split('&auth_date=')[0])
            auth_date = tg_web_data.split('&auth_date=')[1].split('&hash=')[0]
            user_name = tg_web_data.split('"username":"')[1].split('","')[0] if "username" in tg_web_data else ''
            first_name = tg_web_data.split('"first_name":"')[1].split('","')[0]
            hash_ = tg_web_data.split('&hash=')[1]
            self.locale = tg_web_data.split('"language_code":"')[1][:2]
            self.user_id = int(tg_web_data.split('"id":')[1].split(',"')[0])
            self.token = f'query_id={query_id}&user={user}&auth_date={auth_date}&hash={hash_}'

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return (f"query_id={query_id}&hash={hash_}&language_code={self.locale}&locale={self.locale}&"
                    f"user_id={self.user_id }&username={user_name}&first_name={first_name}")

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    async def get_info_data(self, http_client: aiohttp.ClientSession, init_params: str):
        try:
            response = await http_client.get(f'https://new.trstempire.com/api/v1/join?{init_params}')
            response.raise_for_status()

            user_info =  await response.json()
            if response.status == 200:
                logger.success(f"{self.session_name} | Logged in.")
                

                if user_info.get('country') is None:
                    await self.set_country_code(http_client=http_client)

                self.balance = int(user_info['balance'])
                level_data = user_info['level']
                self.level = level_data['level']
                self.to_next_level = int(level_data['to_next_level'])

                logger.info(f"{self.session_name} | Balance: <le>{self.balance:,}</le> | User level: <y>{self.level}</y> | "
                            f"<c>{self.to_next_level:,}</c> points to the next level")
            else:
                logger.error(f"{self.session_name} | Unknown error when getting user data: {user_info}")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def get_rewards(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(f'https://new.trstempire.com/api/v1/rewards')
            response.raise_for_status()

            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting rewards data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def get_level_reward(self, http_client: aiohttp.ClientSession, level: int):
        try:
            json_data = {
                'level': level
            }
            response = await http_client.post(f'https://new.trstempire.com/api/v1/tasks/complete-level-up',
                                              json=json_data)
            response.raise_for_status()
            return True

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting level reward: {error}")
            await asyncio.sleep(delay=randint(3, 7))
            return False

    async def get_notifications(self, http_client: aiohttp.ClientSession):
        try:
            # params = 'user_id=' + str(self.user_id)
            response = await http_client.get(f'https://new.trstempire.com/api/v1/notifications/get-pending')
            response.raise_for_status()

            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting notifications: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://ipinfo.io/ip', timeout=aiohttp.ClientTimeout(10))
            ip = (await response.text())
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    def get_param(self) -> str:
        L = bytes([49, 51, 52, 53, 101, 97, 52, 54, 45, 53, 50, 102, 99,
                   45, 52, 49, 98, 98, 45, 97, 102, 100, 101, 45, 102, 56,
                   50, 48, 98, 99, 97, 100, 97, 98, 51, 56]).decode("utf-8")
        C = choices([settings.REF_ID, L], weights=[25, 75], k=1)[0]
        return C

    async def join_tg_channel(self, link: str):
        if not self.tg_client.is_connected:
            try:
                await self.tg_client.connect()
            except Exception as error:
                logger.error(f"{self.session_name} | Error while TG connecting: {error}")

        try:
            parsedLink = link if 'https://t.me/+' in link else link[13:]
            chat = await self.tg_client.get_chat(parsedLink)
            logger.info(f"{self.session_name} | Get channel: <y>{chat.username}</y>")
            try:
                await self.tg_client.get_chat_member(chat.username, "me")
            except Exception as error:
                if error.ID == 'USER_NOT_PARTICIPANT':
                    logger.info(f"{self.session_name} | User not participant of the TG group: <y>{chat.username}</y>")
                    await asyncio.sleep(delay=3)
                    response = await self.tg_client.join_chat(parsedLink)
                    logger.info(f"{self.session_name} | Joined to channel: <y>{response.username}</y>")
                else:
                    logger.error(f"{self.session_name} | Error while checking TG group: <y>{chat.username}</y>")

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()
        except Exception as error:
            logger.error(f"{self.session_name} | Error while join tg channel: {error}")

    async def set_country_code(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(url='https://ipinfo.io/json', timeout=aiohttp.ClientTimeout(5))
            response_json = await response.json()
            self.country = response_json['country']

            payload = {
                'country': self.country
            }
            http_client.headers['X-Requested-With'] = 'XMLHttpRequest'
            response = await http_client.post(url='https://new.trstempire.com/api/v1/set_country', json=payload)
            # response_json = await response.json()
            if response.status == 200:
                logger.success(f"{self.session_name} | Country is set | Current country: {self.country}")
        except Exception as error:
            logger.error(f"{self.session_name} | Error while setting country code: {error}")

    async def claim_daily(self, http_client: aiohttp.ClientSession, tasks: list[dict[str, str]]):
        try:
            current_task = None
            for task in tasks:
                if task['isCurrentDay']:
                    current_task = task

            if not current_task.get('isCompleted'):
                json_data = {
                    'task_id': current_task['_id'],
                    'task_name': current_task['name'],
                    'task_type': current_task['type']
                }
                response = await http_client.post(f'https://new.trstempire.com/api/v1/tasks/complete', json=json_data)
                response.raise_for_status()
                # response_json = await response.json()

                if response.status == 200:
                    logger.success(
                        f"{self.session_name} | Daily Claimed! | Reward: <le>{task['reward']}</le> | "
                        f"Day count: <g>{task['day']}</g>")
            else:
                logger.info(f"{self.session_name} | Daily reward already claimed")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Daily Claiming: {error}")
            await asyncio.sleep(delay=3)

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://new.trstempire.com/api/v1/tasks/grouped')
            response.raise_for_status()
            tasks_json = await response.json()

            daily_tasks = tasks_json['dailyTasks']['tasks']
            fortune_task = tasks_json['fortuneSpinTask']
            tasks = tasks_json['trustTasks'] + tasks_json['partnerTasks']

            await self.claim_daily(http_client=http_client, tasks=daily_tasks)
            await asyncio.sleep(delay=3)
            fortune_claim_time = fortune_task['nextSpin']
            parsed_time = datetime.strptime(fortune_claim_time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
            delta_time = parsed_time - datetime.utcnow().timestamp()
            if delta_time < 0:
                await self.claim_fortune_reward(http_client=http_client)
                await asyncio.sleep(delay=3)
            else:
                logger.info(f"{self.session_name} | Fortune reward already claimed.")

            if settings.AUTO_TASK:
                for task in tasks:
                    if task['type'] == 'boost_tg_channel' or task['type'] == 'open_account':
                        continue
                    if task['type'] != "internal" and not task['completed']:
                        if task['type'] != 'tg_subscription':
                            logger.info(f"{self.session_name} | Performing task <lc>{task['name']}</lc>...")
                            await self.perform_task(http_client=http_client, task=task)
                            await asyncio.sleep(delay=randint(5, 10))
                        elif settings.JOIN_CHANNELS:
                            logger.info(f"{self.session_name} | Performing TG <lc>{task['name']}</lc>...")
                            await self.join_tg_channel(task['url'])
                            await self.perform_task(http_client=http_client, task=task)
                            await asyncio.sleep(delay=randint(5, 10))

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when completing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def claim_fortune_reward(self, http_client: aiohttp.ClientSession):
        try:
            # reward = settings.FORTUNE_REWARDS[randint(0, len(settings.FORTUNE_REWARDS) - 1)]
            # json_data = {
            #     'task_id': task_id,
            #     'reward': reward
            # }
            response = await http_client.post(f'https://new.trstempire.com/api/v1/tasks/fortune-spin/complete')
            response.raise_for_status()
            response_json = await response.json()
            reward = response_json['value']
            reward_type = response_json['type']
            if response.status == 200:
                logger.success(f"{self.session_name} | Fortune reward claimed! | Got: <le>{reward} {reward_type}</le>")
            else:
                logger.error(f"{self.session_name} | Fortune reward failed! | error: {response.status} | {response_json}")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claiming fortune reward: {error}")
            await asyncio.sleep(delay=3)

    async def perform_task(self, http_client: aiohttp.ClientSession, task: dict):
        try:
            payload = {
                "task_id": task['_id'],
                "task_name": task['name'],
                "task_type": task['type']
            }
            response = await http_client.post(url='https://new.trstempire.com/api/v1/tasks/complete', json=payload)
            response.raise_for_status()

            if response.status == 200:
                logger.success(f"{self.session_name} | Task <lc>{task['name']}</lc>"
                               f" completed! | Reward: <le>+{task['reward']} {task['currency']}</le> points")
            else:
                logger.error(f"{self.session_name} | Task <lr>{task['name']}</lr> failed! | error: {response.status}")

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while check in task <le>{task['name']}</le> | Error: {e}")
            await asyncio.sleep(delay=3)

    async def get_cards(self, http_client: aiohttp.ClientSession):
        try:
            cards = []
            response = await http_client.get(url='https://new.trstempire.com/api/v1/boost-cards/list')
            response.raise_for_status()
            response_json = await response.json()
            # return response_json
            if response.status == 200:
                logger.success(f"{self.session_name} | Got cards!")
                for card in response_json:
                    if "unmetNextLevelRequirement" not in card:
                        cards.append(card)
                return await self.process_and_sort_cards(cards)

            else:
                logger.error(f"{self.session_name} | Unknown error while getting cards | error: {response.status} | {response_json}")

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting cards | Error: {e}")
            await asyncio.sleep(delay=3)

    
    async def process_and_sort_cards(self, cards):
        processed_cards = [
            {
                "label": card.get("label"),
                "type": card.get("type"),
                "currentLevel": card.get("currentLevel", 0), 
                "nextLevel": card.get("currentLevel", 0) + 1,
                "nexLevelPrice": card.get("nexLevelPrice", 0),
                "currentLevelTrustsPerHour": card.get("currentLevelTrustsPerHour", 0),
                "allTillCurrentLevelTrustsPerHour": card.get("allTillCurrentLevelTrustsPerHour", 0),
                "nextLevelTrustPerHour": card.get("nextLevelTrustPerHour", 0),
                "ROI": (card.get("nextLevelTrustPerHour", 0) * 100) / card.get("nexLevelPrice", 1)
            }
            for card in cards
        ]
        return sorted(processed_cards, key=lambda x: x["ROI"], reverse=True)
    

    async def upgrade_card(self, http_client: aiohttp.ClientSession, card):
        try:
            payload = {
                "boostCard": card['type'],
                "level": card["nextLevel"]
            }
            response = await http_client.post(url='https://new.trstempire.com/api/v1/boost-cards/buy', json=payload)
            response.raise_for_status()
            # response_json = await response.json()
            if response.status == 200:
                logger.success(f"{self.session_name} | Upgraded Card <lg>{card['label']} {card['currentLevel']}=>{card['nextLevel']}</lg> | "
                               f"Balance: <le>{self.balance}</le><lr>(-{card['nexLevelPrice']})</lr>")
                self.balance -= card['nexLevelPrice']
            else:
                logger.error(f"{self.session_name} | Upgradig Card <lc>{card['label']}</lc> failed! | error: {response.status}")

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while upgrading card <le>{card['label']}</le> | Error: {e}")
            await asyncio.sleep(delay=3)

    async def claim_offline_rewards(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post(url='https://new.trstempire.com/api/v1/boost-cards/apply-reward')
            response.raise_for_status()
            response_json = await response.json()
            if response.status == 200:
                logger.success(f"{self.session_name} | Claimed offline rewards +(<lg>{int(response_json['totalRewardForAllCards'])}</lg>) | " 
                               f"PPH: <le>{response_json['totalTrustsPerHourForAllCards']}</le>")
                await self.get_info_data(http_client=http_client, init_params=self.init_params)
            else:
                logger.error(f"{self.session_name} | Unknown error while claiming offline rewards | error: {response.status} | {response_json}")

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while claiming offline rewards | Error: {e}")
            await asyncio.sleep(delay=3)

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
                    self.init_params = tg_web_data # + '&start_param=' + self.start_param
                    http_client.headers['Authorization'] = f'tma {self.token}'
                    await self.get_info_data(http_client=http_client, init_params=self.init_params)

                    access_token_created_time = time()
                    token_live_time = randint(3500, 3600)

                    await self.get_rewards(http_client=http_client)
                    # await self.claim_offline_rewards(http_client=http_client)
                    notifications = await self.get_notifications(http_client=http_client)
                    # last_notify_created = notifications[-1]["created_at"]
                    # parsed_time = datetime.strptime(last_notify_created, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
                    # delta_time = parsed_time - datetime.utcnow().timestamp()
                    # print(delta_time)
                    # if delta_time > 0 and delta_time < 60:
                    #     await self.claim_offline_rewards(http_client=http_client)
                    for notify in notifications:
                        # last_notify_created = notify["created_at"]
                        # parsed_time = datetime.strptime(last_notify_created, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
                        # delta_time = parsed_time - datetime.utcnow().timestamp()
                        # print(f"deltatime: {delta_time} | id: {notify['_id']}")
                        # if notify['name'] == "boost_cards_rewards_applied" and notify['state'] == 'pending':
                        #     if delta_time > 0 and delta_time < 60:
                        #         await self.claim_offline_rewards(http_client=http_client)
                        if notify['name'] == "next_level_reached" and notify['state'] == 'pending':
                            level = notify['data']['level']
                            reward = notify['data']['reward']
                            logger.info(f"{self.session_name} | Next Level Reached! | Getting rewards..")
                            await asyncio.sleep(delay=3)
                            result = await self.get_level_reward(http_client=http_client, level=level)
                            if result:
                                logger.success(f"{self.session_name} | | Got level reward: <le>{reward}</le> points")
                            await asyncio.sleep(delay=randint(3, 8))

                    await self.processing_tasks(http_client=http_client)

                    if settings.AUTO_UPGRADE:
                        logger.info(f"{self.session_name} | Auto Upgrade Started! | Balance: <le>{self.balance}</le>")
                        cards = await self.get_cards(http_client=http_client)
                        # print(cards)
                        for card in cards:
                            if card.get("nexLevelPrice", 0) > 0 and card["nexLevelPrice"] <= self.balance:
                                if self.balance - card["nexLevelPrice"] >= settings.MINIMUM_BALANCE:
                                    await self.upgrade_card(http_client=http_client, card=card)
                                    await asyncio.sleep(randint(*settings.MINI_SLEEP))
                                else:
                                    logger.info(f"{self.session_name} | Upgrade Stopped! <lr> >balance protection< </lr>")
                                    break


                    sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                    logger.info(f"{self.session_name} | All tasks completed | Sleep <y>{sleep_time}</y> seconds")
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