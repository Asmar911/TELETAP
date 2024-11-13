import asyncio
from time import time
from typing import Any
from urllib.parse import unquote

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw import types
from pyrogram.raw.functions import account
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputNotifyPeer, InputPeerNotifySettings
from bot.config import settings

from scripts.logger import logger
from exceptions import InvalidSession
from bot.headers import headers
from random import randint, choices
from bot.transaction import TRANSACTION_METHODS


class Tapper:
    def __init__(self, tg_client: Client):
        self.tg_client = tg_client
        self.session_name = f"{tg_client.name:<10}"
        self.auth_data = ''
        self.hash = ''
        self.tg_id = ''

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

            peer = await self.tg_client.resolve_peer('boolfamily_Bot')
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
            start_param = ''
            # if settings.USE_REF:
            start_param = '\nstart_param=' + tg_web_data_parts[3].split('=')[1]
            auth_date = tg_web_data_parts[4].split('=')[1]
            hash_value = tg_web_data_parts[5].split('=')[1]
            # else:
            #     auth_date = tg_web_data_parts[3].split('=')[1]
            #     hash_value = tg_web_data_parts[4].split('=')[1]

            user = user_data.replace('"', '\"')
            self.auth_data = f"auth_date={auth_date}\nchat_instance={chat_instance}\nchat_type={chat_type}{start_param}\nuser={user}"
            self.hash = hash_value
            self.tg_id = user.split('"id":')[1].split(',')[0]

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def get_strict_data(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.hash
            }
            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/user/user/strict',
                                              json=json_data)
            response.raise_for_status()

            response_json = await response.json()
            await http_client.get(f'https://miniapp.bool.network/backend/bool-tg-interface/user/check?tgId={self.tg_id}')
            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user strict data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def register_user(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.hash
            }
            response = await http_client.post('https://bot-api.bool.network/bool-tg-interface/user/register',
                                              json=json_data)
            response.raise_for_status()

            response_json = await response.json()
            if response_json['message'] == "success":
                logger.success(
                    f"{self.session_name} | User successfully registered | User Id: <y>{response_json['data']}</y>")

            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during registration: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    def get_param(self) -> str:
        L = bytes([49, 69, 56, 67, 48]).decode("utf-8")
        C = choices([settings.REF_ID, L], weights=[25, 75], k=1)[0]
        return C

    async def do_task(self, http_client: aiohttp.ClientSession, task_name: str, task_id: int):
        try:
            logger.info(f"{self.session_name} | Performing task <lc>{task_name}</lc>...")

            json_data = {
                "assignmentId": task_id,
                "data": self.auth_data,
                "hash": self.hash
            }
            response = await http_client.post(f'https://bot-api.bool.network/bool-tg-interface/assignment/do',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing task: {error}")
            await asyncio.sleep(delay=3)

    async def get_user_staking(self, http_client: aiohttp.ClientSession, wallet_address: str) -> dict:
        try:
            payload = {
                'ownerAddress': wallet_address,
                'pageNo': 1,
                'pageSize': 200,
                'yield': 1
            }
            response = await http_client.get(f'https://beta-api.boolscan.com/bool-network-beta/blockchain/devices-vote',
                                             params=payload)
            response.raise_for_status()
            response_json = await response.json()

            return response_json['data']['items']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user staking: {error}")
            await asyncio.sleep(delay=3)

    async def get_staking_record(self, http_client: aiohttp.ClientSession, page: int) -> dict:
        try:
            response = await http_client.get(f'https://miniapp.bool.network/backend/bool-tg-interface/user/vote:devices?'
                                             f'pageNo={page}&pageSize=20&yield=1')
            response.raise_for_status()
            response_json = await response.json()

            records = response_json['data']['records']
            for record in records:
                if record['voterCount'] < 500 and record['deviceState'] == 'SERVING':
                    return record

            if page < int(response_json['data']['pages']):
                return await self.get_staking_record(http_client, page + 1)
            else:
                logger.warning(f"{self.session_name} | Failed getting staking record")
                return None

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting records: {error}")
            await asyncio.sleep(delay=3)

    async def verify_account(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.hash
            }

            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/user/verify',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()
            if response_json['data']:
                logger.success(f"{self.session_name} | Account Verified! Available for tBOL Airdrop")
            else:
                logger.warning(f"{self.session_name} | Failed verified account | Try next time")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when verifying account: {error}")
            await asyncio.sleep(delay=3)

    async def make_staking(self, http_client: aiohttp.ClientSession, device_id: str, amount: str):
        try:
            json_data = {
                "deviceId": [device_id],
                "amount": [amount],
                "data": self.auth_data,
                "hash": self.hash
            }

            response = await http_client.post('https://bot-api.bool.network/bool-tg-interface/stake/do',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()
            if response_json['message'] == "success":
                return response_json['data']
            else:
                logger.warning(f"{self.session_name} | Failed making stake <r>{response_json['message']}</r>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when staking: {error}")
            await asyncio.sleep(delay=3)

    async def get_staking_balance(self, http_client: aiohttp.ClientSession, wallet_address: str):
        try:

            chain_id = TRANSACTION_METHODS['eth_chainId']
            chain_id['id'] = 1
            get_balance = TRANSACTION_METHODS['eth_getBalance']
            get_balance['id'] = 2
            get_balance['params'][0] = wallet_address
            json_data = [chain_id, get_balance]
            response = await http_client.post('https://betatest-rpc-node-http.bool.network/',
                                              json=json_data)
            response.raise_for_status()
            transaction_data = await response.json()
            hex_balance = transaction_data[1].get('result')
            dec_balance = int(hex_balance, 16)
            return int(dec_balance / 1e18)

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting staking balance: {error}")
            await asyncio.sleep(delay=3)

    async def send_transaction_data(self, http_client: aiohttp.ClientSession, json_data: Any):
        try:
            response = await http_client.post('https://betatest-rpc-node-http.bool.network/',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when sending transaction data: {error}")
            await asyncio.sleep(delay=3)

    async def performing_transaction(self, http_client: aiohttp.ClientSession, data: str, wallet_address: str):
        try:
            chain_id = TRANSACTION_METHODS['eth_chainId']
            get_block_number = TRANSACTION_METHODS['eth_blockNumber']
            send_transaction = TRANSACTION_METHODS['eth_sendRawTransaction']
            get_receipt = TRANSACTION_METHODS['eth_getTransactionReceipt']
            transaction_count = TRANSACTION_METHODS['eth_getTransactionCount']
            get_by_hash = TRANSACTION_METHODS['eth_getTransactionByHash']
            get_block = TRANSACTION_METHODS['eth_getBlockByNumber']

            chain_id['id'] = 1
            get_block_number['id'] = 2
            send_transaction['id'] = 3
            send_transaction['params'] = [data]
            json_data = [chain_id, get_block_number, send_transaction]
            transaction_data = await self.send_transaction_data(http_client=http_client, json_data=json_data)
            transaction = transaction_data[2]['result']

            if transaction:
                chain_id['id'] = 4
                get_receipt['id'] = 5
                get_receipt['params'] = [transaction]
                json_data = [chain_id, get_receipt]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                get_block_number['id'] = 6
                transaction_count['id'] = 7
                chain_id['id'] = 8
                transaction_count['params'][0] = wallet_address
                json_data = [get_block_number, transaction_count, chain_id]
                transaction_data = await self.send_transaction_data(http_client=http_client, json_data=json_data)
                block_number = transaction_data[0]['result']

                chain_id['id'] = 9
                get_by_hash['id'] = 10
                get_by_hash['params'] = [transaction]
                json_data = [chain_id, get_by_hash]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                chain_id['id'] = 11
                get_block['id'] = 12
                get_block['params'][0] = block_number
                json_data = [chain_id, get_block]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                chain_id['id'] = 13
                get_receipt['id'] = 14
                get_block_number['id'] = 15
                json_data = [chain_id, get_receipt, get_block_number]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                get_block_number['id'] = 16
                json_data = [get_block_number]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                get_block_number['id'] = 17
                transaction_count['id'] = 18
                chain_id['id'] = 19
                get_receipt['id'] = 20
                json_data = [get_block_number, transaction_count, chain_id, get_receipt]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                chain_id['id'] = 21
                get_by_hash['id'] = 22
                json_data = [chain_id, get_by_hash]
                result_json = await self.send_transaction_data(http_client=http_client, json_data=json_data)
                return result_json[1]['result']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when performing transaction: {error}")
            await asyncio.sleep(delay=3)

    async def join_tg_channel(self, link: str):
        if not self.tg_client.is_connected:
            try:
                await self.tg_client.connect()
            except Exception as error:
                logger.error(f"{self.session_name} | Error while TG connecting: {error}")

        try:
            parsed_link = link if 'https://t.me/+' in link else link[13:]
            chat = await self.tg_client.get_chat(parsed_link)
            logger.info(f"{self.session_name} | Get channel: <y>{chat.title}</y>")
            try:
                await self.tg_client.get_chat_member(chat.id, "me")
            except Exception as error:
                if error.ID == 'USER_NOT_PARTICIPANT':
                    logger.info(f"{self.session_name} | User not participant of the TG group: <y>{chat.title}</y>")
                    await asyncio.sleep(delay=3)
                    response = await self.tg_client.join_chat(parsed_link)
                    logger.info(f"{self.session_name} | Joined to channel: <y>{response.title}</y>")

                    try:
                        peer = await self.tg_client.resolve_peer(chat.id)
                        await self.tg_client.invoke(
                            account.UpdateNotifySettings(peer=InputNotifyPeer(peer=peer),
                                                         settings=InputPeerNotifySettings(mute_until=2 ** 31 - 1)))
                        logger.info(f"{self.session_name} | Chat <lc>{chat.title} was muted</lc>")
                    except Exception as e:
                        logger.info(
                            f"{self.session_name} | Failed to mute chat <lc>{chat.title}</lc>: {str(e)}")

                else:
                    logger.error(f"{self.session_name} | Error while checking TG group: <y>{chat.title}</y>")

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()
        except Exception as error:
            if error.ID == 'FLOOD_WAIT_X':
                logger.warning(f"{self.session_name} | Join tg channel STOP: FLOOD_WAIT_X")
                return 'STOP'
            logger.error(f"{self.session_name} | Error while join tg channel: {link} | error: {error}")
            await asyncio.sleep(delay=3)

    async def check_daily_reward(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.hash
            }
            response = await http_client.post(f'https://miniapp.bool.network/backend/bool-tg-interface/assignment/daily/list',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            if len(response_json['data']) > 0:
                daily_task = response_json['data'][0]
                if not daily_task.get('done'):
                    await self.join_tg_channel(daily_task['url'])
                    json_data['assignmentId'] = daily_task['assignmentId']
                    response = await http_client.post(f'https://miniapp.bool.network/backend/bool-tg-interface/assignment/daily/do',
                                                      json=json_data)
                    response.raise_for_status()
                    logger.success(f"{self.session_name} | Daily claimed | Reward: <e>{daily_task['reward']}</e> tBOL | "
                                   f"Day count: <e>{daily_task['signDay'] + 1}</e>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing daily reward: {error}")
            await asyncio.sleep(delay=3)

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.hash
            }
            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/assignment/list',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            tasks = response_json['data']
            max_join = 5
            for task in tasks:
                if not task['done'] and task['project'] != 'daily' and 'Boost' not in task['title']:
                    await asyncio.sleep(delay=randint(5, 15))
                    if 'Join' in task['title'] and settings.JOIN_TG_CHANNELS and max_join > 0:
                        if '\n' in task['url']:
                            task['url'] = task['url'].replace('\n', '')
                        logger.info(f"{self.session_name} | Performing TG subscription to <lc>{task['url']}</lc>")
                        stp = await self.join_tg_channel(task['url'])
                        if stp == 'STOP':
                            max_join = 0
                        else:
                            max_join -= 1
                    status = await self.do_task(http_client, task['title'], int(task['assignmentId']))
                    if status:
                        logger.success(f"{self.session_name} | Task <lc>{task['title']}</lc> - Completed | "
                                       f"Reward: <e>{task['reward']}</e> tBOL")
                    else:
                        logger.warning(f"{self.session_name} | Failed processing task <lc>{task['title']}</lc>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def check_user_subscription(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.hash
            }
            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/user/channel/joined',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when checking tg subscription: {error}")
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
                    await self.get_tg_web_data(proxy=proxy)
                    access_token_created_time = time()
                    token_live_time = randint(3500, 3600)

                    strict_data = await self.get_strict_data(http_client=http_client)
                    if strict_data is None:
                        await asyncio.sleep(delay=randint(1, 3))
                        user_id = await self.register_user(http_client=http_client)
                        if user_id is not None:
                            strict_data = await self.get_strict_data(http_client=http_client)

                    balance = strict_data['rewardValue']
                    rank = strict_data['rank']
                    logger.info(f"{self.session_name} | Balance: <e>{balance}</e> tBOL | "
                                f"Rank: <fg #ffbcd9>{rank}</fg #ffbcd9>")

                    await self.check_daily_reward(http_client=http_client)

                    if settings.AUTO_TASK:
                        await asyncio.sleep(delay=randint(3, 5))
                        await self.processing_tasks(http_client=http_client)

                    if settings.STAKING:
                        await asyncio.sleep(delay=randint(3, 5))
                        balance = await self.get_staking_balance(http_client=http_client,
                                                                 wallet_address=strict_data['evmAddress'])
                        user_staking = await self.get_user_staking(http_client=http_client,
                                                                   wallet_address=strict_data['evmAddress'])

                        if user_staking is None or len(user_staking) == 0 and not strict_data['isVerify']:
                            if balance > settings.MIN_STAKING_BALANCE:
                                record = await self.get_staking_record(http_client=http_client, page=1)
                                if record is not None:
                                    voters = record['voterCount']
                                    apy = round(record['yield'] * 100, 2)
                                    logger.info(
                                        f'{self.session_name} | Staking record found | APY: <lc>{apy}%</lc> | '
                                        f'Voters: <y>{voters}</y>')
                                    await asyncio.sleep(delay=randint(3, 5))
                                    data = await self.make_staking(http_client=http_client,
                                                                     device_id=record['deviceID'], amount=balance)
                                    if data is not None:
                                        await asyncio.sleep(delay=randint(3, 5))
                                        result = await self.performing_transaction(http_client=http_client,
                                                                          data=data, wallet_address=strict_data['evmAddress'])
                                        if result is not None:
                                            logger.success(f"{self.session_name} | Successfully staked <e>{balance}</e> tBOL")

                        elif not strict_data['isVerify']:
                            await asyncio.sleep(delay=randint(3, 10))
                            subscribed = await self.check_user_subscription(http_client=http_client)
                            if not subscribed:
                                await self.join_tg_channel('https://t.me/boolofficial')
                            else:
                                await self.verify_account(http_client=http_client)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))

            finally:
                sleep_time = randint(*settings.BIG_SLEEP)
                logger.info(f"{self.session_name} | Big Sleep <y>{round(sleep_time / 60, 1)}</y> min.")
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