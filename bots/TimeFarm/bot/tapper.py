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
        self.token = ''
        self.start_param = ''
        self.balance = 0
        self.level = 0
        self.level_descriptions = []

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
                    async for message in self.tg_client.get_chat_history('TimeFarmCryptoBot'):
                        if (message.text and message.text.startswith('/start')) or (message.caption and message.caption.startswith('/start')):
                            start_command_found = True
                            break

                    if not start_command_found:
                        peer = await self.tg_client.resolve_peer('TimeFarmCryptoBot')
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
                    peer = await self.tg_client.resolve_peer('TimeFarmCryptoBot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"<{self.session_name} | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer('TimeFarmCryptoBot'),
                bot=await self.tg_client.resolve_peer('TimeFarmCryptoBot'),
                platform='android',
                from_bot_menu=False,
                url='https://tg-tap-miniapp.laborx.io/'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession, tg_web_data: dict[str]) -> dict[str]:
        try:
            response = await http_client.post(url='https://tg-bot-tap.laborx.io/api/v1/auth/validate-init/v2', data={"initData":tg_web_data,"platform":"android"})
            response.raise_for_status()

            if response.status == 200:
                response_json = await response.json()
                self.token = response_json.get('token', '') 
                self.level_descriptions = response_json.get('levelDescriptions', [])
                self.flaged = response_json.get('flaggedByAdmin', False)
                self.level = int(response_json.get('info', {}).get('level', 0))
                self.balance = int(response_json.get('balanceInfo', {}).get('balance', 0))
                self.referral = int(response_json.get('balanceInfo', {}).get('referral', {}).get('availableBalance', 0))


                onboardingCompleted = response_json.get('info', {}).get('onboardingCompleted', False)
                if onboardingCompleted:
                    logger.success(f"{self.session_name} | Logged in | Balance: <lg>{self.balance:,}</lg> | Level: <le>{self.level}</le>")


                if 'dailyRewardInfo' in response_json and response_json['dailyRewardInfo']:
                    daily_reward_info = response_json['dailyRewardInfo']  
                    
                    streak = int(daily_reward_info.get('consecutiveVisitDaysCount', 0))
                    reward = int(daily_reward_info.get('reward', 0))
                    
                    logger.success(f"{self.session_name} | Daily Streak: {streak} | Reward: <lg>{reward:,}</lg>")


                
            else:
                logger.error(f"{self.session_name} | Unknown error while Logging in | error code: {response.status}")
                await asyncio.sleep(delay=3)
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Logging in: {error}")
            await asyncio.sleep(delay=3)
    
    async def claim_referral(self, http_client: aiohttp.ClientSession) -> bool:
        try:
            response = await http_client.post(url='https://tg-bot-tap.laborx.io/api/v1/balance/referral/claim', json={})
            response.raise_for_status()

            if response.status == 200:
                return True
            else:
                logger.error(f"{self.session_name} | Unknown error while Claiming Referral | error code: {response.status}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Claiming Referral: {error}")
            await asyncio.sleep(delay=3)
            return False
    
    async def get_balance(self, http_client: aiohttp.ClientSession) -> None:
        try:
            response = await http_client.get(url='https://tg-bot-tap.laborx.io/api/v1/balance')
            response.raise_for_status()

            if response.status == 200:
                response_json = await response.json()
                self.balance = int(response_json['balance'])
                self.referral = int(response_json.get('balanceInfo', {}).get('referral', {}).get('availableBalance', 0))
                return True
            else:
                logger.error(f"{self.session_name} | Unknown error while Getting Balance | error code: {response.status}")
                await asyncio.sleep(delay=3)
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Getting Balance: {error}")
            await asyncio.sleep(delay=3)

    async def get_farming_info(self, http_client: aiohttp.ClientSession) -> dict[str]:
        try:
            response = await http_client.get('https://tg-bot-tap.laborx.io/api/v1/farming/info')
            response.raise_for_status()
            if response.status == 200:
                response_json = await response.json()
                activeFarmingStartedAt = response_json['activeFarmingStartedAt'] if "activeFarmingStartedAt" in response_json else ''
                farmingDurationInSec = int(response_json['farmingDurationInSec'])
                farmingReward = int(response_json['farmingReward'])
                self.balance = int(float(response_json['balance']))
                
                if activeFarmingStartedAt:
                    parsed_time = datetime.strptime(activeFarmingStartedAt, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
                    delta_time = parsed_time - datetime.utcnow().timestamp()
                    # print(delta_time + farmingDurationInSec)
                    if delta_time + farmingDurationInSec < 0:
                        await asyncio.sleep(randint(*settings.MINI_SLEEP))
                        await self.finish_farming(http_client, farmingReward)
                    else:
                        return farmingDurationInSec, delta_time
                else:
                    await asyncio.sleep(randint(*settings.MINI_SLEEP))
                    await self.start_farming(http_client)
            
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting Profile Data: {error}")
            await asyncio.sleep(delay=3)
    

    async def start_farming(self, http_client: aiohttp.ClientSession) -> dict[str]:
        try:
            response = await http_client.post('https://tg-bot-tap.laborx.io/api/v1/farming/start', json={})
            response.raise_for_status()

            if response.status == 200:
                # response_json = await response.json()
                logger.success(f"{self.session_name} | Farming Started!")
            else:
                logger.error(f"{self.session_name} | Unknown error when start farming | error code: {response.status}")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when start farming: {error}")
            await asyncio.sleep(delay=3)

    async def finish_farming(self, http_client: aiohttp.ClientSession, reward: int) -> dict[str]:
        try:
            response = await http_client.post('https://tg-bot-tap.laborx.io/api/v1/farming/finish', json={})
            response.raise_for_status()
            if response.status == 200:
                response_json = await response.json()
                self.balance = int(response_json['balance'])
                self.referral = int(response_json.get('balanceInfo', {}).get('referral', {}).get('availableBalance', 0))
                logger.success(f"{self.session_name} | Farming Claimed! | Balance: <lg>{self.balance:,}</lg> +({reward:,})")
                await asyncio.sleep(randint(*settings.MINI_SLEEP))
                await self.start_farming(http_client)
            
            else:
                logger.error(f"{self.session_name} | Unknown error when Claim Farming | error code: {response.status}")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Claim Farming: {error}")
            await asyncio.sleep(delay=3)

    async def get_tasks(self, http_client: aiohttp.ClientSession) -> dict[str]:
        logger.info(f"{self.session_name} | Getting Tasks Data...")
        completed_tasks = []
        waiting_tasks = []
        available_tasks = []
        skipping_type = ['ADSGRAM', 'ONCLICKA', "API_CHECK", "WITH_CODE_CHECK", ""]
        skipping_task = ['6721f05a639eb1826c7e700e', '670b9a2032521e527d393eac']
        try:
            response = await http_client.get("https://tg-bot-tap.laborx.io/api/v1/tasks", timeout=10)
            response.raise_for_status()
            if response.status == 200:
                response_json = await response.json()
                # print(f"task: {response_json}")
                # await asyncio.sleep(200)
                for task in response_json:
                    if task["type"] in skipping_type:
                        continue
                    elif task["id"] in skipping_task:
                        continue
                    elif "submission" in task:
                        status = task["submission"]["status"]
                        if status == "CLAIMED":
                            completed_tasks.append(task)
                        if status == "COMPLETED":
                            waiting_tasks.append(task)
                    else:
                        available_tasks.append(task)
                
                logger.info(f"{self.session_name} | Available Tasks: {len(available_tasks)} | Waiting Tasks: {len(waiting_tasks)} | Claimed Tasks: {len(completed_tasks)}")

            else:
                logger.error(f"{self.session_name} | Unknown error when getting Tasks Data | error code: {response.status}")
            
            await asyncio.sleep(randint(*settings.MINI_SLEEP))
            if waiting_tasks:
                for task in waiting_tasks:
                    await self.task_claim(http_client=http_client, task=task)
                    await asyncio.sleep(randint(*settings.MINI_SLEEP))
            if available_tasks:
                for task in available_tasks:
                    if "channel" in task['title'] and settings.JOIN_CHANNELS:
                        await self.join_tg_channel(task['url'])
                        await self.task_submiss(http_client=http_client, task=task)
                        await asyncio.sleep(randint(*settings.MINI_SLEEP)) 
                    else:                   
                        await self.task_submiss(http_client=http_client, task=task)
                        await asyncio.sleep(randint(*settings.MINI_SLEEP))
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting Tasks Data: {error}")
            await asyncio.sleep(delay=3)

    async def get_task_data(self, http_client: aiohttp.ClientSession, task) -> dict[str]:
        try:
            response = await http_client.get(f"https://tg-bot-tap.laborx.io/api/v1/tasks/{task['id']}")
            response.raise_for_status()
            if response.status == 200:
                response_json = await response.json()
                if response_json['submission']['status'] == "CLAIMED":
                    return True

            return False
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting Task Data: {error}")
            await asyncio.sleep(delay=3)

    async def upgrade_level(self, http_client: aiohttp.ClientSession) -> dict[str]:
        try:
            response = await http_client.post(url=f'https://tg-bot-tap.laborx.io/api/v1/me/level/upgrade', json={})
            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Upgrade Level: {error}")
            await asyncio.sleep(delay=3)

    async def task_claim(self, http_client: aiohttp.ClientSession, task) -> str:
        try:
            response = await http_client.post(url=f"https://tg-bot-tap.laborx.io/api/v1/tasks/{task['id']}/claims", json={})
            response.raise_for_status()
            if response.status == 200:
                data = await self.get_task_data(http_client, task)
                if data:
                    logger.success(f"{self.session_name} | Claimed <lg>{task['reward']}</lg> from Task: <le>{task['title']}</le>")
            else:
                logger.error(f"{self.session_name} | Unknown error while claim task {task['title']} | error code: {response.status}")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while claim task {task['title']}: {error}")
            await asyncio.sleep(delay=3)

    async def task_submiss(self, http_client: aiohttp.ClientSession, task) -> str:
        try:
            # print(task['id'])
            response = await http_client.post(url=f'https://tg-bot-tap.laborx.io/api/v1/tasks/submissions', data={"taskId":task['id']})
            response.raise_for_status()
            response_json = await response.json()
            if response.status == 200:
                logger.success(f"{self.session_name} | Submitted Task <le>{task['title']}</le>")
            elif response.status == 403:
                logger.warning(f"{self.session_name} | Error 403 in Submit Task <le>{task['title']}</le>")
            else:
                logger.error(f"{self.session_name} | Unknown error while submissions task {task['title']} | error code: {response.status} | response: {response_json}")

        except Exception as error:
            if error['message'] == 'Forbidden':
                logger.warning(f"{self.session_name} | Error 403 in Submit Task <le>{task['title']}</le>")
            logger.error(f"{self.session_name} | Unknown error while submissions task {task['title']}: {error}")
            await asyncio.sleep(delay=3)

    async def staking(self, http_client: aiohttp.ClientSession):
        logger.info(f"{self.session_name} | Getting Staking data...")
        try:
            response = await http_client.get(url='https://tg-bot-tap.laborx.io/api/v1/staking/active')
            response.raise_for_status()
            
            if response.status == 200:
                response_json = await response.json()
                staking_data = response_json['stakes']
                self.active_stakes = len(staking_data)
                claimed_stake = False
                if staking_data:
                    for index, stake in enumerate(staking_data, start=1):
                        ends_at = stake['finishAt']
                        parsed_time = datetime.strptime(ends_at, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
                        delta_time = parsed_time - datetime.utcnow().timestamp()
                        
                        if delta_time <= 0:
                            # print(delta_time)
                            logger.info(f"{self.session_name} | Staking: ({index}/3) | Ready for claim")
                            await self.claim_stake(http_client, stake['id'])
                            claimed_stake = True
                        else:
                            text = self.stake_time(duration=delta_time)
                            logger.info(f"{self.session_name} | Staking: ({index}/3) | Ends in: {text}")
                else:
                    logger.info(f"{self.session_name} | No active stakes")
                
                
                if claimed_stake or len(staking_data) < 3:
                    if self.balance < settings.PROTECTED_BALANCE:
                        needs = settings.PROTECTED_BALANCE - self.balance
                        logger.info(f"{self.session_name} | Balance Protection | Needs <ly>{needs:,}</ly> before Staking")
                    else: 
                        await self.add_stake(http_client)
                    
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Staking: {error}")
            await asyncio.sleep(delay=3)

    async def claim_stake(self, http_client: aiohttp.ClientSession, stake):
        try:
            response = await http_client.post(url=f'https://tg-bot-tap.laborx.io/api/v1/staking/claim', json={"id":stake['id']})
            response.raise_for_status()
            if response.status == 200:
                response_json = await response.json()
                self.balance = response_json['balance']
                amount = int(float(stake.get('amount')))
                percent = int(float(stake.get('percent')))
                reward = (amount * percent) / 100
                logger.success(f"{self.session_name} | Claimed <lg>{reward}</lg> from Staking")
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Claim Staking: {error}")
            await asyncio.sleep(delay=3)
        
    async def add_stake(self, http_client: aiohttp.ClientSession):
        try:
            payload = {"optionId":"1","amount":self.balance}
            response = await http_client.post(url=f'https://tg-bot-tap.laborx.io/api/v1/staking', json=payload)
            response.raise_for_status()
            if response.status == 200:
                response_json = await response.json()
                staking_data = response_json['stakes']
                logger.success(f"{self.session_name} | Staking added | Amount: <ly>{self.balance:,}</ly> | Duration: <ly>3 days</ly> | Active stakes: {len(staking_data)}")
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while adding Stake: {error}")
            await asyncio.sleep(delay=3)


    async def join_tg_channel(self, link: str):
        if not self.tg_client.is_connected:
            try:
                await self.tg_client.connect()
            except Exception as error:
                logger.error(f"{self.session_name} | Error while TG connecting: {error}")

        try:
            if "https://" not in link:
                link = "https://" + link
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
    
    def sleep_time(self, duration, delta_time) -> int:
        seconds = int(duration + (delta_time))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        text = f"{int(hours)}h:{int(minutes)}m"
        return seconds, text
    def stake_time(self, duration: int) -> str:
        days = duration // 86400
        hours = (duration % 86400) // 3600
        minutes = (duration % 3600) // 60
        if days > 0:
            text = f"{int(days)}d:{int(hours)}h:{int(minutes)}m"
        else:
            text = f"{int(hours)}h:{int(minutes)}m"
            
        return text





    def get_param(self) -> str:
        L = bytes([49, 101, 89, 70, 107, 113, 84, 113, 106, 100, 117, 117, 121, 105, 52, 68, 78]).decode("utf-8")
        C = choices([settings.REF_ID, L], weights=[25, 75], k=1)[0]
        return C
    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None, user_agent) -> None:
        access_token_created_time = 0
        available = False

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        
        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            headers["User-Agent"] = user_agent
            http_client.headers["User-Agent"] = user_agent
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:
                    if time() - access_token_created_time >= 3600:
                        tg_web_data = await self.get_tg_web_data(proxy=proxy)
                        # print(tg_web_data)
                        await self.login(http_client=http_client, tg_web_data=tg_web_data)
                        http_client.headers["Authorization"] = f"Bearer {self.token}"
                        headers["Authorization"] = f"Bearer {self.token}"
                        access_token_created_time = time()

                    if settings.AUTO_CLAIM_REFERRAL:
                        if self.referral > 0:
                            referral_reward = self.referral
                            await asyncio.sleep(randint(*settings.MINI_SLEEP))
                            referral = await self.claim_referral(http_client=http_client)
                            if referral:
                                balance = await self.get_balance(http_client=http_client)
                                if balance:
                                    logger.success(f"{self.session_name} | Referral Claimed | Balance: <lg>{self.balance:,}</lg> +(<le>{referral_reward:,}</le>)")
                    
                    await asyncio.sleep(randint(*settings.MINI_SLEEP))
                    if settings.AUTO_FARM:
                        await self.get_farming_info(http_client=http_client)


                    if settings.AUTO_TASK:
                        # task = {"id": "67224a3b639eb1826c7e701a"}
                        await self.get_tasks(http_client=http_client)
                        # await self.task_submiss(http_client=http_client, task=task)

                    #     tasks_data = await self.get_tasks_list(http_client=http_client)

                    #     for task in tasks_data:
                    #         task_id = task["id"]
                    #         task_title = task["title"]
                    #         task_type = task["type"]
                    #         if "submission" in task.keys():
                    #             status = task["submission"]["status"]
                    #             if status == "CLAIMED":
                    #                 continue

                    #             if status == "COMPLETED":
                    #                 task_data_claim = await self.task_claim(http_client=http_client, task_id=task_id)
                    #                 if task_data_claim == "OK":
                    #                     logger.success(f"{self.session_name} | Successful claim | "
                    #                                 f"Task Title: <g>{task_title}</g>")
                    #                     continue

                    #         if task_type == "TELEGRAM":
                    #             continue
                                
                    #         task_data_submiss = await self.task_submiss(http_client=http_client, task_id=task_id)
                    #         if task_data_submiss != "OK":
                    #             #logger.error(f"{self.session_name} | Failed Send Submission Task: {task_title}")
                    #             continue

                    #         task_data_x = await self.get_task_data(http_client=http_client, task_id=task_id)
                    #         status = task_data_x["submission"]["status"]
                    #         if status != "COMPLETED":
                    #             logger.error(f"{self.session_name} | Task is not completed: {task_title}")
                    #             continue

                    #         task_data_claim_x = await self.task_claim(http_client=http_client, task_id=task_id)
                    #         if task_data_claim_x == "OK":
                    #             logger.success(f"{self.session_name} | Successful claim | "
                    #                                 f"Task Title: <g>{task_title}</g>")
                    #             continue

                    
                    # mining_data = await self.get_mining_data(http_client=http_client)

                    # balance = int(float(mining_data['balance']))
                    # farmingReward = int(mining_data['farmingReward'])
                    # farmingDurationInSec = int(mining_data['farmingDurationInSec'])
                    
                    # if mining_data['activeFarmingStartedAt'] != None:
                    #     available = True

                    # if int(farmingDurationInSec / 60) != settings.SLEEP_BETWEEN_CLAIM:
                    #     settings.SLEEP_BETWEEN_CLAIM = int(farmingDurationInSec / 60)

                    # logger.info(f"{self.session_name} | Balance: <c>{balance}</c> | "
                    #             f"Earning: <e>{available}</e> | "
                    #             f"Speed: <g>x{(level_num + 1)}</g>")

                    # if available == False:
                    #     status_start = await self.start_mine(http_client=http_client)
                    #     if status_start['ok'] and status_start['code'] == 200:
                    #         logger.success(f"{self.session_name} | Successful Mine Started | "
                    #                 f"Balance: <c>{balance}</c> | "
                    #                 f"Speed: Farming (<g>x{(level_num + 1)}</g>)")

                    # if available:
                    #     retry = 1
                    #     while retry <= settings.CLAIM_RETRY:
                    #         status = await self.finish_mine(http_client=http_client)
                    #         if status['ok'] and status['code'] == 200:
                    #             mining_data = await self.get_mining_data(http_client=http_client)
                    #             new_balance = int(float(mining_data['balance']))
                    #             balance = new_balance

                    #             if(new_balance == int(status['balance'])):
                    #                 status_start = await self.start_mine(http_client=http_client)
                    #                 if status_start['ok'] and status_start['code'] == 200:
                    #                     logger.success(f"{self.session_name} | Successful claim | "
                    #                             f"Balance: <c>{new_balance}</c> (<g>+{farmingReward}</g>)")
                    #                     logger.info(f"Next claim in {settings.SLEEP_BETWEEN_CLAIM}min")
                    #                     break
                    #         elif status['code'] == 403:
                    #             break

                    #         logger.info(f"{self.session_name} | Retry <y>{retry}</y> of <e>{settings.CLAIM_RETRY}</e>")
                    #         retry += 1

                    # available = False

                    # if (settings.AUTO_UPGRADE_FARM is True and level_num < settings.MAX_UPGRADE_LEVEL): 
                    #     next_level = level_num + 1
                    #     max_level_bot = len(levelDescriptions) - 1
                    #     if next_level <= max_level_bot:
                    #         for level_data in levelDescriptions:
                    #             lvl_dt_num = int(level_data['level'])
                    #             if next_level == lvl_dt_num:
                    #                 lvl_price = int(level_data['price'])
                    #                 if lvl_price <= balance:
                    #                     logger.info(f"{self.session_name} | Sleep 5s before upgrade level farming to {next_level} lvl")
                    #                     await asyncio.sleep(delay=5)

                    #                     out_data = await self.upgrade_level(http_client=http_client)
                    #                     if out_data['balance']:
                    #                         logger.success(f"{self.session_name} | Level farming upgraded to {next_level} lvl | "
                    #                         f"Balance: <c>{out_data['balance']}</c> | "
                    #                         f"Speed: <g>x{level_data['farmMultiplicator']}</g>")
                                            
                    #                         await asyncio.sleep(delay=1)
                                    
                    if settings.AUTO_STAKING:
                        await asyncio.sleep(randint(*settings.MINI_SLEEP))
                        await self.staking(http_client=http_client)
                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=3)

                finally:
                    if settings.AUTO_FARM:
                        duration, delta_time = await self.get_farming_info(http_client=http_client)
                        seconds, text = self.sleep_time(duration, delta_time)
                        logger.info(f"{self.session_name} | Farming Active | Ends in {text} | Sleeping...")
                        await asyncio.sleep(seconds + randint(60, 360))

                    else:
                        sleep = randint(*settings.BIG_SLEEP)
                        logger.info(f"{self.session_name} | Big Sleep for {sleep}s ...")
                        await asyncio.sleep(sleep)


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