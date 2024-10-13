import asyncio
import secrets
from datetime import datetime
from time import time
from urllib.parse import unquote, quote
import aiohttp
import pytz
import traceback
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
from .headers import headers
from random import randint, uniform, choices
from bot.parser import get_app_version


# api endpoint
api_profile = 'https://cexp.cex.io/api/v2/getUserInfo/'  # POST
api_convert = 'https://cexp.cex.io/api/v2/convert/'  # POST
api_claimBTC = 'https://cexp.cex.io/api/v2/claimCrypto/'  # POST
api_tap = 'https://cexp.cex.io/api/v2/claimMultiTaps'  # POST
api_data = 'https://cexp.cex.io/api/v2/getGameConfig'  # post
api_priceData = 'https://cexp.cex.io/api/v2/getConvertData'  # post
api_claimRef = 'https://cexp.cex.io/api/v2/claimFromChildren'  # post
api_checkref = 'https://cexp.cex.io/api/v2/getChildren'  # post
api_startTask = 'https://cexp.cex.io/api/v2/startTask'  # post
api_checkTask = 'https://cexp.cex.io/api/v2/checkTask'  # post
api_claimTask = 'https://cexp.cex.io/api/v2/claimTask'  # post
api_checkCompletedTask = 'https://cexp.cex.io/api/v2/getUserTasks' # post
api_getUserCard = 'https://cexp.cex.io/api/v2/getUserCards' #post
api_buyUpgrade = 'https://cexp.cex.io/api/v2/buyUpgrade' #post
api_buyboost = 'https://cexp.cex.io/api/v2/buyBoost' #post
api_getSpecialOffer = 'https://cexp.cex.io/api/v2/getUserSpecialOffer' # post
api_startSpecialOffer = 'https://cexp.cex.io/api/v2/startUserSpecialOffer' #post
api_checkSpecialOffer = 'https://cexp.cex.io/api/v2/checkUserSpecialOffer' #post
api_claimSpecialOffer = 'https://cexp.cex.io/api/v2/claimUserSpecialOffer' #post

class Tapper:
    def __init__(self, tg_client: Client, app_version):
        self.tg_client = tg_client
        self.session_name = f"{tg_client.name:<10}"
        self.version = app_version
        self.first_name = ''
        self.last_name = ''
        self.user_id = ''
        self.user_hash = ''
        self.Total_Point_Earned = 0
        self.Total_Game_Played = 0
        self.btc_balance = 0
        self.coin_balance = 0
        self.cexp_balance = 0
        self.multiTapsPower = 0
        self.multiTapsEnergyLimit = 0
        self.tapAttemptsPerInterval = 0
        self.task = None
        self.card = None
        self.newTasks = []
        self.startedTasks = []
        self.completedTasks = []
        self.special_task = []
        self.ready_to_check_special_task = []
        self.skip = ['register_on_cex_io', 'boost_telegram', 'invite_1_friend', 'invite_5_friends', 'invite_10_friends', 'invite_20_friends', 'invite_50_friends', 'invite_100_friends' , 'invite500Friends' , 'invite1000Friends', 'make_deposit', 'make_buy_crypto', 'make_convert', 'make_trade', 'play_piggypiggy_tap_game', 'subscribe_crypto_garden_telegram', 'join_btc_garden_twitter']
        self.card1 = None
        self.potential_card = {}
        self.multi = 1000000
        self.energy = 1000
        self.cexp_balance = 0
        self.multi_tap = 1
        self.energy_limit = 1000


    async def get_tg_web_data(self, proxy: str | None) -> str:
        logger.info(f"{self.session_name} | Getting user data...")
        if settings.REF_ID != "":
            ref_param = choices([settings.REF_ID, "1716712060572190"], weights=[75, 25], k=1)[0]
        else:
            ref_param = "1716712060572190"
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
                    start_command_found = False
                    async for message in self.tg_client.get_chat_history('cexio_tap_bot'):
                        if (message.text and message.text.startswith('/start')) or (
                                message.caption and message.caption.startswith('/start')):
                            start_command_found = True
                            break
                    if not start_command_found:
                        peer = await self.tg_client.resolve_peer('cexio_tap_bot')
                        await self.tg_client.invoke(
                            functions.messages.StartBot(
                                bot=peer,
                                peer=peer,
                                start_param=ref_param,
                                random_id=randint(1, 9999999),
                            )
                        )

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('cexio_tap_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | FloodWait {fl}")
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='ios',
                from_bot_menu=False,
                url="https://cexp4.cex.io",
            ))
            auth_url = web_view.url
            # print(unquote(auth_url))
            tg_web_data = unquote(
                string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            # print("tg_web_data", tg_web_data)

            self.user_id = tg_web_data.split('"id":')[1].split(',"first_name"')[0]
            self.first_name = tg_web_data.split('"first_name":"')[1].split('","last_name"')[0]
            self.last_name = tg_web_data.split('"last_name":"')[1].split('","username"')[0]
            self.user_hash = tg_web_data.split('hash=')[1].split('&')[0]

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def get_user_info(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        # print(http_client.headers)
        response = await http_client.post(api_profile, json=data)
        if response.status == 200:
            try:
                json_response = await response.json()
                data_response = json_response['data']
                self.user_level = data_response['level']
                self.coin_balance = data_response['balance_USD']
                self.multi = 10**data_response['precision_BTC']
                self.cexp_balance = int(data_response.get('balance_CEXP', 0))
                self.btc_balance = int(data_response['balance_BTC']) / self.multi
                self.multiTapsPower = int(data_response['multiTapsPower'])
                self.multiTapsEnergyLimit = int(data_response['multiTapsEnergyLimit'])
                self.tapAttemptsPerInterval = int(data_response['tapAttemptsPerInterval'])

                # print(f"{self.session_name}: {data_response['balance_BTC']}")
                logger.info(
                    f"{self.session_name} | Level: {self.user_level} | Balance: <yellow>{self.coin_balance}</yellow> | Btc balance: <yellow>{self.btc_balance}</yellow> | Power: <yellow>{self.cexp_balance}</yellow> CEXP")
            except Exception as e:
                logger.error(f"Error while getting user data: {e} .Try again after 30s")
                await asyncio.sleep(30)
                return
        else:
            logger.error(f"Error while getting user data. Response {response.status}. Try again after 30s")
            await asyncio.sleep(30)

    async def get_user_special_task(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": authToken,
            "platform": "android",
            "data": {}
        }

        response = await http_client.post(api_getSpecialOffer, json=data)
        if response.status == 200:
            json_response = await response.json()
            for task in json_response['data']:
                if task['type'] != "social" and task['type'] != "learn_earn":
                    continue
                elif task['state'] == "NONE":
                    self.special_task.append(task)
                elif task['state'] == "ReadyToCheck":
                    logger.info(f"{self.session_name} | Task: {task['taskId']} ready for check...")
                    self.ready_to_check_special_task.append(task)
        else:
            logger.warning(f"{self.session_name} | Failed to get special tasks data. Response code: {response.status}")

    async def start_special_task(self, http_client: aiohttp.ClientSession, authToken, offerId, taskName):
        data = {
            "devAuthData": int(self.user_id),
            "authData": authToken,
            "platform": "android",
            "data": {
                "specialOfferId": str(offerId)
            }
        }

        response = await http_client.post(api_startSpecialOffer, json=data)
        if response.status == 200:
            logger.success(f"{self.session_name} | Successfully started special offer: {taskName}.")
            return True
        else:
            logger.warning(f"{self.session_name} | Failed to start special offer data. Response code: {response.status}")
            return False
    async def claim_special_task(self, http_client: aiohttp.ClientSession, authToken, offerId, taskName):
        data = {
            "devAuthData": int(self.user_id),
            "authData": authToken,
            "platform": "android",
            "data": {
                "specialOfferId": str(offerId)
            }
        }
        response = await http_client.post(api_claimSpecialOffer, json=data)
        if response.status == 200:
            logger.success(f"{self.session_name} | Successfully claimed special offer: <cyan>{taskName}</cyan>")
        else:
            logger.warning(
                f"{self.session_name} | Failed to claim special offer. Response code: {response.status}")
            return False

    async def check_special_task(self, http_client: aiohttp.ClientSession, authToken, offerId, taskName):
        data = {
            "devAuthData": int(self.user_id),
            "authData": authToken,
            "platform": "android",
            "data": {
                "specialOfferId": str(offerId)
            }
        }

        response = await http_client.post(api_checkSpecialOffer, json=data)
        if response.status == 200:
            check = False
            json_response = await response.json()
            for task in json_response['data']:
                if task['specialOfferId'] == str(offerId):
                    if task['state'] == "ReadyToClaim":
                        check = await self.claim_special_task(http_client, authToken, offerId, taskName)
                        break
                    else:
                        logger.info(f"{self.session_name} | Task: {task['taskId']} wait for check...")
                        break
            if check:
                return True
            else:
                return False
        else:
            logger.warning(f"{self.session_name} | Failed to check special offer. Response code: {response.status}")
            return False

    async def sync_taps(self, http_client: aiohttp.ClientSession, authToken, start_energy):
        time_unix = int((time()) * 1000)
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {
                "tapsEnergy": str(start_energy),
                "tapsToClaim": "0",
                "tapsTs": time_unix
            }
        }
        # print(int((time()) * 1000) - time_unix)
        response = await http_client.post(api_tap, json=data)
        if response.status == 200:
            json_response = await response.json()
            data_response = json_response['data']
            self.coin_balance = data_response['balance_USD']
            logger.success(f"{self.session_name} | Tap Synced Successfully| Energy: {start_energy}")
            await asyncio.sleep(3)
        else:
            json_response = await response.json()
            if "too slow" in json_response['data']['reason']:
                logger.error(f'{self.session_name} | <red>Tap Sync failed | please stop the code and open the bot in telegram then tap 1-2 times and run this code again. it should be worked!</red>')
                logger.info(f"Response: {json_response}")
            else:
                print(json_response)
                logger.error(f'{self.session_name} | <red>Tap Sync failed | response code: {response.status}</red>')


    async def tap(self, http_client: aiohttp.ClientSession, authToken, taps, remaining_energy, SLEEP):
        time_unix = int((time()) * 1000)
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {
                "tapsEnergy": str(remaining_energy),
                "tapsToClaim": str(taps),
                "tapsTs": time_unix
            }
        }
        # print(int((time()) * 1000) - time_unix)
        response = await http_client.post(api_tap, json=data)
        if response.status == 200:
            json_response = await response.json()
            data_response = json_response['data']
            self.coin_balance = data_response['balance_USD']
            logger.success(f"{self.session_name} | Tapped <cyan>{taps}</cyan> times | balance: <cyan>{data_response['balance_USD']}</cyan> | Energy left: {remaining_energy} | Sleep: {SLEEP}s")
        else:
            json_response = await response.json()
            if "too slow" in json_response['data']['reason']:
                logger.error(f'{self.session_name} | <red>Tap failed | ({taps}) | please stop the code and open the bot in telegram then tap 1-2 times and run this code again. it should be worked!</red>')
            elif "fast taps" in json_response['data']['reason']:
                pass
                logger.info(f"Response: {json_response}")
            else:
                print(json_response)
                logger.error(f'{self.session_name} | <red>Tap failed | ({taps}) | response code: {response.status}</red>')

    async def claim_crypto(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        response = await http_client.post(api_claimBTC, json=data)
        if response.status == 200:
            json_response = await response.json()
            data_response = json_response['data']["BTC"]
            try:
                self.multi = 10 ** int(data_response['precision_BTC'])
                self.btc_balance = int(data_response['balance_BTC']) / self.multi
            except:
                logger.info(f"{self.session_name} | Offline mining not cliamable...")
                return None
            logger.info(
                f"{self.session_name} | Claimed offline mining <cyan>+{int(data_response['claimedAmount']) / self.multi}</cyan> BTC | BTC Balance: <cyan>{int(data_response['balance_BTC']) / self.multi}</cyan>")
        else:
            logger.error(f"{self.session_name} | <red>Claim ofline mining failed | response code: {response.status}</red>")

    async def getConvertData(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        response = await http_client.post(api_priceData, json=data)
        if response.status == 200:
            json_response = await response.json()
            data_response = json_response['convertData']['lastPrices']
            return data_response[-1]
        else:
            logger.error(f"{self.session_name} | <red>Can't convert ! | response code: {response.status}</red>")
            return None

    async def convertBTC(self, http_client: aiohttp.ClientSession, authToken):
        price = await self.getConvertData(http_client, authToken)
        if price:
            data = {
                "devAuthData": int(self.user_id),
                "authData": str(authToken),
                "platform": "ios",
                "data": {
                    "fromCcy": "BTC",
                    "toCcy": "USD",
                    "price": str(price),
                    "fromAmount": str(self.btc_balance)
                }
            }
            response = await http_client.post(api_convert, json=data)
            if response.status == 200:
                json_response = await response.json()
                data_response = json_response['convert']
                # self.coin_balance = data_response['balance_USD']
                self.coin_balance = int(float(data_response['balance_USD']))
                logger.success(
                    f"{self.session_name} | Successfully convert <yellow>{self.btc_balance}</yellow> to <yellow>{int(round(float(self.btc_balance)))*int(round(float(price)))}</yellow> coin | Coin balance: <yellow>{data_response['balance_USD']}</yellow>")
            else:
                logger.error(f"{self.session_name} | <red>Error While trying to convert | response code: {response.status}</red>")

    async def checkref(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        response = await http_client.post(api_checkref, json=data)
        if response.status == 200:
            json_response = await response.json()
            return json_response['data']['totalRewardsToClaim']
        else:
            return 0

    async def claim_pool(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        response = await http_client.post(api_claimRef, json=data)
        if response.status == 200:
            json_response = await response.json()
            logger.success(
                f"{self.session_name} | Successfully Claimed Pool: <yellow>+{int(json_response['data']['claimed_BTC']) / self.multi} BTC</yellow> | BTC balance: <yellow>{int(json_response['data']['balance_BTC']) / self.multi}</yellow>")
        else:
            logger.error(f"{self.session_name} | <red>Error While trying to claim from pool | Error code {response.status}</red>")

    async def fetch_data(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        response = await http_client.post(api_data, json=data)
        if response.status == 200:
            json_response = await response.json(content_type=None)
            # print(json_response)
            self.task = json_response['tasksConfig']
            self.card = json_response['upgradeCardsConfig']
            logger.success(f"{self.session_name} | Successfully fetched user cards and tasks")
        else:
            logger.error(f"{self.session_name} | <red>Error While trying to get data | Code {response.status}</red>")

    async def getUserTask(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        response = await http_client.post(api_checkCompletedTask, json=data)
        if response.status == 200:
            json_response = await response.json()
            user_tasks = json_response['tasks']
            # print(json_response)
            for task in json_response['tasks']:
                if json_response['tasks'][task]['state'] == "NONE":
                    self.newTasks.append(task)
                elif json_response['tasks'][task]['state'] == "ReadyToCheck":
                    self.startedTasks.append(task)
                elif json_response['tasks'][task]['state'] == "Claimed":
                    self.completedTasks.append(task)
            return user_tasks
        else:
            logger.error(f"{self.session_name} | <red>Error while fetching tasks data | code {response.status}</red>")
            return None

    async def claimTask(self, http_client: aiohttp.ClientSession, authToken, taskId, type):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {
                "taskId": taskId
            }
        }
        MINI_SLEEP = randint(settings.MINI_SLEEP[0], settings.MINI_SLEEP[1])
        logger.info(f"{self.session_name} | Sleeping for {MINI_SLEEP}s before claiming task: {taskId} | Type: {type}")
        await asyncio.sleep(delay=MINI_SLEEP)
        response = await http_client.post(api_claimTask, json=data)
        if response.status == 200:
            json_response = await response.json()
            reward = json_response['data']['claimedBalance']
            type = json_response['data']['task']['type']
            logger.success(f"{self.session_name} | Successfully claimed <yellow>{reward}</yellow> from task: {taskId} | Type: {type}")
        else:
            logger.error(f"{self.session_name} | <red>Failed to claim task: {taskId}. Response: {response.status}</red>")

    async def checkTask(self, http_client: aiohttp.ClientSession, authToken, taskId, type):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {
                "taskId": taskId
            }
        }
        MINI_SLEEP = randint(settings.MINI_SLEEP[0], settings.MINI_SLEEP[1])
        logger.info(f"{self.session_name} | Sleeping for {MINI_SLEEP}s before checking task: {taskId} | Type: {type}")
        await asyncio.sleep(delay=MINI_SLEEP)
        response = await http_client.post(api_checkTask, json=data)
        if response.status == 200:
            json_response = await response.json()
            if json_response['data']['state'] == "ReadyToClaim":
                await self.claimTask(http_client, authToken, taskId, type)
            else:
                logger.info(f"{self.session_name} | Wait for check task: {taskId}")
        else:
            logger.error(f"{self.session_name} | <red>Failed to check task: {taskId}. Response: {response.status}</red>")

    async def startTask(self, http_client: aiohttp.ClientSession, authToken, taskId, type):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {
                "taskId": taskId
            }
        }
        MINI_SLEEP = randint(settings.MINI_SLEEP[0], settings.MINI_SLEEP[1])
        logger.info(f"{self.session_name} | Sleeping for {MINI_SLEEP}s before starting task: {taskId} | Type: {type}")
        await asyncio.sleep(delay=MINI_SLEEP)
        response = await http_client.post(api_startTask, json=data)
        if response.status == 200:
            logger.success(f"{self.session_name} | Successfully started task: {taskId}")
        else:
            if response.status == 500:
                self.skip.append(taskId)
            logger.error(f"{self.session_name} | <red>Failed to start task: {taskId}. Response: {response.status}</red>")

    async def getUserCard(self, http_client: aiohttp.ClientSession, authToken):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {}
        }
        response = await http_client.post(api_getUserCard, json=data)
        if response.status == 200:
            json_response = await response.json()
            return json_response['cards']
        else:
           return None

    async def find_potential(self):
        for category in self.card:
            for card in category['upgrades']:
                # print(card)
                if card['upgradeId'] in self.card1:
                    card_lvl = self.card1[card['upgradeId']]['lvl']
                    if len(card['levels']) <= card_lvl:
                        continue
                    if len(card['levels']) > 0:
                        potential = card['levels'][card_lvl][0]/card['levels'][card_lvl][2]
                        self.potential_card.update({
                            potential: {
                                "upgradeId": card['upgradeId'],
                                "cost": card['levels'][card_lvl][0],
                                "effect": card['levels'][card_lvl][2],
                                "categoryId": category['categoryId'],
                                "nextLevel": card_lvl + 1,
                                "effectCcy": "CEXP",
                                "ccy": "USD",
                                "dependency": card['dependency']
                            }
                        })
                else:
                    if len(card['levels']) > 0:
                        if card['levels'][0][2] != 0:
                            potential = card['levels'][0][0]/card['levels'][0][2]
                            self.potential_card.update({
                                potential: {
                                    "upgradeId":  card['upgradeId'],
                                    "cost": card['levels'][0][0],
                                    "effect": card['levels'][0][2],
                                    "categoryId": category['categoryId'],
                                    "nextLevel": 1,
                                    "effectCcy": "CEXP",
                                    "ccy": "USD",
                                    "dependency": card['dependency']
                                }
                            })

    def checkDependcy(self, dependency):
        if len(dependency) == 0:
            return True
        if dependency['upgradeId'] not in self.card1:
            return False
        if self.card1[dependency['upgradeId']]['lvl'] >= dependency['level']:
            return True
        return False

    async def buyUpgrade(self, http_client: aiohttp.ClientSession, authToken, Buydata, remaining_balance):
        data = {
            "devAuthData": int(self.user_id),
            "authData": str(authToken),
            "platform": "ios",
            "data": {
                "categoryId": Buydata['categoryId'],
                "ccy": Buydata['ccy'],
                "cost": Buydata['cost'],
                "effect": Buydata['effect'],
                "effectCcy": Buydata['effectCcy'],
                "nextLevel": Buydata['nextLevel'],
                "upgradeId": Buydata['upgradeId']
            }
        }
        
        response = await http_client.post(api_buyUpgrade, json=data)
        if response.status == 200:
            logger.success(f"{self.session_name} | <green>Successfully upgraded <blue>{Buydata['upgradeId']}</blue> to level <blue>{Buydata['nextLevel']}</blue> | Remaining balance: <blue>{remaining_balance}</blue></green>")
            return True
        else:
            logger.error(f"{self.session_name} | <red>Error while upgrade card {Buydata['upgradeId']} to lvl {Buydata['nextLevel']}. Response code: {response.status}</red>")
            return False

    def generate_random_hex_string(self):
        # Generate a 32-byte random string (256 bits)
        random_bytes = secrets.token_bytes(32)
        # Convert the bytes to a hex string
        return random_bytes.hex()



    async def run(self, proxy: str | None, user_agent) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers["user-agent"] = user_agent
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)
        authToken = ""
        token_live_time = randint(3500, 3600)
        while True:
            try:
                if time() - access_token_created_time >= token_live_time or authToken == "":
                    
                    logger.info(f"{self.session_name} | Update auth token...")
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    # with open("bots/cexio/bot/x-appl-version.txt", "r") as f:
                    #     version = f.read()
                    
                    http_client.headers.update({'x-appl-version': str(self.version)})
                    # http_client.headers.update({"x-request-userhash": self.user_hash})
                    # print(http_client.headers)
                    # print(self.user_id)
                    authToken = tg_web_data
                    
                    access_token_created_time = time()
                    token_live_time = randint(3500, 3600)
                logger.success(f"{self.session_name} | Successfully logged in.")

                # Getting user info
                # user_hash = self.generate_random_hex_string()
                # print(f"user_hash {user_hash}")
                http_client.headers.update({"x-request-userhash": str(self.user_hash)})
                await self.get_user_info(http_client, authToken)
                await asyncio.sleep(delay=3)

                # Getting user cards and tasks
                await self.fetch_data(http_client, authToken)
                await asyncio.sleep(delay=3)

                # Claiming ofline rewards
                await self.claim_crypto(http_client, authToken)
                await asyncio.sleep(delay=3)

                # Claiming pool bonus
                if settings.AUTO_CLAIM_SQUAD_BONUS:
                    pool_balance = await self.checkref(http_client, authToken)
                    if float(pool_balance) > 0:
                        await self.claim_pool(http_client, authToken)
                    else:
                        logger.info(f"{self.session_name} | No pool balance to claim | continuing...")
                else:
                    logger.info(f"{self.session_name} | Auto claim squad bonus is disabled | skipping...")
                await asyncio.sleep(delay=3)

                # Converting BTC to USD
                if settings.AUTO_CONVERT:
                    if self.btc_balance >= settings.MINIMUM_TO_CONVERT:
                        await self.convertBTC(http_client, authToken)   
                    else:
                        logger.info(f"{self.session_name} | No balance to convert | continuing...")
                else:
                    logger.info(f"{self.session_name} | Auto convert is disabled | skipping...")
                await asyncio.sleep(delay=3)


                # Fetching cards and tasks data
                # if self.card is None or self.task is None:
                #     await self.fetch_data(http_client, authToken)
                #     await asyncio.sleep(3)

                # Claiming tasks
                if settings.AUTO_TASK and self.task:

                    MINI_SLEEP = randint(settings.MINI_SLEEP[0], settings.MINI_SLEEP[1])
                    logger.info(f"{self.session_name} | Sleeping for {MINI_SLEEP}s before claiming special tasks...")
                    await asyncio.sleep(delay=MINI_SLEEP)

                    await self.get_user_special_task(http_client, authToken)
                    if len(self.special_task) > 0:
                        for task in self.special_task:
                            check = await self.start_special_task(http_client,authToken,task['specialOfferId'],task['taskId'])
                            if check:
                                self.special_task.remove(task)
                        await asyncio.sleep(uniform(2, 3))
                    elif len(self.ready_to_check_special_task) > 0:
                        for task in self.ready_to_check_special_task:
                            check = await self.check_special_task(http_client, authToken,task['specialOfferId'], task['taskId'])
                            if check:
                                self.ready_to_check_special_task.remove(task)
                            await asyncio.sleep(uniform(2,3))
                    else:
                        logger.info(f"{self.session_name} | No special tasks now!")

                    
                    MINI_SLEEP = randint(settings.MINI_SLEEP[0], settings.MINI_SLEEP[1])
                    logger.info(f"{self.session_name} | Sleeping for {MINI_SLEEP}s before claiming normal tasks...")
                    await asyncio.sleep(delay=MINI_SLEEP)

                    user_task = await self.getUserTask(http_client, authToken)
                    # logger.info(f"{self.session_name} | user tasks: {user_task}")
                    # await asyncio.sleep(delay=60)
                    # print(f"self.tasks: {self.task}\n\nuser_task: {user_task}\n\n")
                    if user_task:
                        for task in self.task:
                            # print(task)
                            if task['taskId'] in self.skip:
                                continue
                            elif task['taskId'] in self.completedTasks:
                                continue
                            # elif task['type'] != "learn_earn":
                            #     continue
                            elif task['taskId'] in self.newTasks:
                                await self.startTask(http_client, authToken, task['taskId'], task['type'])
                            elif task['taskId'] in self.startedTasks:
                                await self.checkTask(http_client, authToken, task['taskId'], task['type'])
                            # else:
                            #     await self.startTask(http_client, authToken, task['taskId'], task['type'])
                        else:
                            logger.info(f"{self.session_name} | All tasks claimed | continuing...")

                else:
                    logger.info(f"{self.session_name} | Auto task is disabled | skipping...")
                await asyncio.sleep(delay=3)


                


                

                # runtime = 3
                # Sending taps
                if settings.AUTO_TAP:
                    start_energy = self.multiTapsEnergyLimit
                    await self.sync_taps(http_client, authToken, start_energy)

                    MINI_SLEEP= randint(settings.MINI_SLEEP[0], settings.MINI_SLEEP[1])
                    logger.info(f"{self.session_name} | Sleeping for {MINI_SLEEP}s before tapping...")
                    await asyncio.sleep(delay=MINI_SLEEP)
                    # await self.claim_crypto(http_client, authToken)
                    
                    

                    while start_energy > 0:
                        # logger.info(f"{self.session_name} | energy {energy}")
                        SLEEP = randint(settings.SLEEP_BETWEEN_TAPS[0], settings.SLEEP_BETWEEN_TAPS[1])
                        ATTEMPT = randint(3, self.tapAttemptsPerInterval)
                        taps = int(SLEEP * self.multiTapsPower * ATTEMPT)
                        remaining_energy = int(start_energy - taps) #+ int(SLEEP * 3)
                        if taps <= start_energy and start_energy >= settings.MIN_ENERGY:
                            # logger.info(f"{self.session_name} | Sleep: {SLEEP}s | Attempt: {ATTEMPT} | Tapping {taps} | energy {remaining_energy}")
                            await self.tap(http_client, authToken, taps, remaining_energy, SLEEP)
                            # await asyncio.sleep(1)
                            start_energy -= (taps)
                            await asyncio.sleep(delay=SLEEP)

                        else:
                            logger.warning(f"{self.session_name} | Not enough energy to send {taps} taps | energy {start_energy}")
                            # logger.info(f"{self.session_name} | Sleeping {SLEEP}s before continuing...")
                            # await asyncio.sleep(delay=3)
                            break

                else:
                    logger.info(f"{self.session_name} | Auto tap is disabled | Skipping...")
                await asyncio.sleep(delay=3)


                # while runtime > 0:
                #     await self.claim_crypto(http_client, authToken)
                #     runtime -= 1
                # UPGRADE_SLEEP = randint(15, 25)
                # logger.info(f"{self.session_name} | Sleeping {UPGRADE_SLEEP}s before next upgrade...")
                # await asyncio.sleep(UPGRADE_SLEEP)

                # Upgrading the best cards
                if settings.AUTO_BUY_UPGRADE:
                    MINI_SLEEP = randint(*settings.MINI_SLEEP)
                    logger.info(f"{self.session_name} | Sleeping for {MINI_SLEEP}s befor start upgrading cards | Balance: {int(round(float(self.coin_balance)))} coins")
                    # await asyncio.sleep(MINI_SLEEP)
                    upgrade_balance = int(round(float(self.coin_balance)))
                    while upgrade_balance > settings.BALANCE_TO_SAVE:
                        #await self.get_user_info(http_client, authToken)
                        self.card1 = await self.getUserCard(http_client, authToken)
                        if self.card1:
                            await self.find_potential()
                            sorted_potential_card = dict(sorted(self.potential_card.items()))
                            # print(sorted_potential_card)
                            for card in sorted_potential_card:
                                if self.checkDependcy(sorted_potential_card[card]['dependency']):
                                    if int(sorted_potential_card[card]['cost']) <= int(round(float(upgrade_balance))) and (upgrade_balance - int(sorted_potential_card[card]['cost'])) > settings.BALANCE_TO_SAVE:
                                        remaining_balance = upgrade_balance - int(sorted_potential_card[card]['cost'])
                                        UPGRADE_SLEEP = randint(10, 20)
                                        logger.info(f"{self.session_name} | Sleeping for {UPGRADE_SLEEP}s before upgrading card: {sorted_potential_card[card]['upgradeId']} to level {sorted_potential_card[card]['nextLevel']} with {sorted_potential_card[card]['cost']} coins")
                                        await asyncio.sleep(delay=UPGRADE_SLEEP)
                                        check = await self.buyUpgrade(http_client, authToken, sorted_potential_card[card], remaining_balance)
                                        if check:
                                            self.potential_card.pop(card)
                                        # break
                                        upgrade_balance -= (int(sorted_potential_card[card]['cost']))
                                        # print(f"Upgrade Balance: {upgrade_balance} | Remaining Balance: {remaining_balance}")
                                    else:
                                        # logger.info(f"{self.session_name} | Not enough coins to buy {sorted_potential_card[card]['upgradeId']} with price {sorted_potential_card[card]['cost']} | Needs <red>{sorted_potential_card[card]['cost'] - upgrade_balance}</red> | Remaining balance: {upgrade_balance}| Skipping...")
                                        # await asyncio.sleep(delay=3)
                                        continue
                                    
                            else:
                                logger.info(f"{self.session_name} | Upgrading round <green>FINISHED</green> | Continue...")
                                break
                    else:
                        logger.info(f"{self.session_name} | Stop upgrading | <green>Balance Protection</green> | Remaining balance: {upgrade_balance} | Continue...")
                else:               
                    logger.info(f"{self.session_name} | Auto buy upgrade is disabled | Skipping...")
                await asyncio.sleep(delay=3)
                    

                
            except InvalidSession as error:
                raise error

            except Exception as error:
                traceback.print_exc()
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))

            finally:
                # await self.claim_crypto(http_client, authToken)
                BIG_SLEEP = randint(settings.BIG_SLEEP[0], settings.BIG_SLEEP[1]) #randint(60, 120)
                logger.info(f"{self.session_name} | Big sleep For {BIG_SLEEP} seconds...")
                await asyncio.sleep(delay=BIG_SLEEP)





async def run_tapper(tg_client: Client, user_agent: str, proxy: str | None, app_version):
    try:
        if not settings.ACCOUNTS_MOOD_SEQUENTIAL:
            _sleep = randint(*settings.LOGIN_SLEEP)
            logger.info(f"{tg_client.name} | Bot will start in {_sleep}s ...")
            await asyncio.sleep(_sleep)
            await Tapper(tg_client=tg_client, app_version=app_version).run(proxy=proxy, user_agent=user_agent)
        else:
            await Tapper(tg_client=tg_client, app_version=app_version).run(proxy=proxy, user_agent=user_agent)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")


















