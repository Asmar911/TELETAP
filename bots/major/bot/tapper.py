import asyncio
from random import randint, choices
from urllib.parse import unquote

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.functions import account
import time
import json
from pyrogram.raw.types import InputBotAppShortName, InputNotifyPeer, InputPeerNotifySettings
from bot.config import settings
from typing import Callable
import functools
from scripts.logger import logger
from exceptions import InvalidSession
from .headers import headers


def error_handler(func: Callable):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            await asyncio.sleep(1)
    return wrapper

class Tapper:
    def __init__(self, tg_client: Client, proxy: str):
        self.tg_client = tg_client
        self.session_name = f"{tg_client.name:<10}"
        self.proxy = proxy
        self.tg_web_data = None
        self.tg_client_id = 0
        # self.skip_tasks = ['Status Purchase', 'One-time Stars Purchase', 'Binance x TON', 'Donate rating', 'Invite more Friends', 'Boost Major channel', 'Promote TON blockchain', 'Stars Purchase', 'Extra Stars Purchase']
        self.skip_tasks = ['33', '21', '20', '6', '4', '8', '15', '32', '34']
    async def get_tg_web_data(self) -> str:
        
        if self.proxy:
            proxy = Proxy.from_str(self.proxy)
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
            
            while True:
                try:
                    peer = await self.tg_client.resolve_peer('major')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | Sleep {fls}s")
                    await asyncio.sleep(fls + 3)
            
            ref_id = choices([settings.REF_ID, "153623395"], weights=[75, 25], k=1)[0]
            
            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotAppShortName(bot_id=peer, short_name="start"),
                platform='android',
                write_allowed=True,
                start_param=ref_id
            ))

            auth_url = web_view.url
            tg_web_data = unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])

            me = await self.tg_client.get_me()
            self.tg_client_id = me.id
            
            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return ref_id, tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error: {error}")
            await asyncio.sleep(delay=3)
        
        
    async def join_and_mute_tg_channel(self, link: str):
        link = link if 'https://t.me/+' in link else link[13:]
        if link == 'money':
            return
        
        if not self.tg_client.is_connected:
            try:
                await self.tg_client.connect()
            except Exception as error:
                logger.error(f"{self.session_name} | (Task) Connect failed: {error}")
        try:
            chat = await self.tg_client.get_chat(link)
            chat_username = chat.username if chat.username else link
            chat_id = chat.id
            try:
                await self.tg_client.get_chat_member(chat.username, "me")
            except Exception as error:
                if error.ID == 'USER_NOT_PARTICIPANT':
                    await asyncio.sleep(delay=3)
                    response = await self.tg_client.join_chat(link)
                    logger.info(f"{self.session_name} | Joined to channel: <y>{response.username}</y>")
                    
                    try:
                        peer = await self.tg_client.resolve_peer(chat_id)
                        await self.tg_client.invoke(account.UpdateNotifySettings(
                            peer=InputNotifyPeer(peer=peer),
                            settings=InputPeerNotifySettings(mute_until=2147483647)
                        ))
                        logger.info(f"{self.session_name} | Successfully muted chat <y>{chat_username}</y>")
                    except Exception as e:
                        logger.info(f"{self.session_name} | (Task) Failed to mute chat <y>{chat_username}</y>: {str(e)}")
                    
                    
                else:
                    logger.error(f"{self.session_name} | (Task) Error while checking TG group: <y>{chat_username}</y>")

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()
        except Exception as error:
            logger.error(f"{self.session_name} | (Task) Error while join tg channel: {link} | {error}")

    
    @error_handler
    async def make_request(self, http_client, method, endpoint=None, url=None, **kwargs):
        full_url = url or f"https://major.bot/api{endpoint or ''}"
        response = await http_client.request(method, full_url, **kwargs)
        response.raise_for_status()
        return await response.json()
    
    @error_handler
    async def login(self, http_client, init_data, ref_id):
        response = await self.make_request(http_client, 'POST', endpoint="/auth/tg/", json={"init_data": init_data})
        if response and response.get("access_token", None):
            return response
        return None
    
    @error_handler
    async def get_daily(self, http_client):
        return await self.make_request(http_client, 'GET', endpoint="/tasks/?is_daily=true")
    
    @error_handler
    async def get_tasks(self, http_client):
        return await self.make_request(http_client, 'GET', endpoint="/tasks/?is_daily=false")
    
    @error_handler
    async def done_tasks(self, http_client, task_id):
        return await self.make_request(http_client, 'POST', endpoint="/tasks/", json={"task_id": task_id})
    
    @error_handler
    async def claim_swipe_coins(self, http_client):
        response = await self.make_request(http_client, 'GET', endpoint="/swipe_coin/")
        if response and response.get('success') is True:
            logger.info(f"{self.session_name} | Start game <y>SwipeCoins</y>")
            coins = randint(settings.SWIPE_COIN[0], settings.SWIPE_COIN[1])
            payload = {"coins": coins }
            await asyncio.sleep(55)
            response = await self.make_request(http_client, 'POST', endpoint="/swipe_coin/", json=payload)
            if response and response.get('success') is True:
                return coins
            return 0
        return 0

    @error_handler
    async def claim_hold_coins(self, http_client):
        response = await self.make_request(http_client, 'GET', endpoint="/bonuses/coins/")
        if response and response.get('success') is True:
            logger.info(f"{self.session_name} | Start game <y>HoldCoins</y>")
            coins = randint(settings.HOLD_COIN[0], settings.HOLD_COIN[1])
            payload = {"coins": coins }
            await asyncio.sleep(55)
            response = await self.make_request(http_client, 'POST', endpoint="/bonuses/coins/", json=payload)
            if response and response.get('success') is True:
                return coins
            return 0
        return 0

    @error_handler
    async def claim_roulette(self, http_client):
        response = await self.make_request(http_client, 'GET', endpoint="/roulette/")
        if response and response.get('success') is True:
            logger.info(f"{self.session_name} | Start game <y>Roulette</y>")
            await asyncio.sleep(10)
            response = await self.make_request(http_client, 'POST', endpoint="/roulette/")
            if response:
                return response.get('rating_award', 0)
            return 0
        return 0
    
    @error_handler
    async def visit(self, http_client):
        return await self.make_request(http_client, 'POST', endpoint="/user-visits/visit/?")
        
    @error_handler
    async def streak(self, http_client):
        return await self.make_request(http_client, 'POST', endpoint="/user-visits/streak/?")
    
    @error_handler
    async def get_detail(self, http_client):
        detail = await self.make_request(http_client, 'GET', endpoint=f"/users/{self.tg_client_id}/")
        
        return detail.get('rating') if detail else 0
    
    @error_handler
    async def join_squad(self, http_client):
        return await self.make_request(http_client, 'POST', endpoint="/squads/2211646206/join/?")
    
    @error_handler
    async def get_squad(self, http_client):
        return await self.make_request(http_client, 'GET', endpoint=f"/squads/2211646206?")
    
    @error_handler
    async def puvel_puzzle(self, http_client):
        
        start = await self.make_request(http_client, 'GET', endpoint="/durov/")
        if start and start.get('success', False):
            logger.info(f"{self.session_name} | Start game <y>Puzzle</y>")
            async with aiohttp.ClientSession() as session:
                async with session.get("https://raw.githubusercontent.com/GravelFire/TWFqb3JCb3RQdXp6bGVEdXJvdg/master/answer.py") as response:
                    status = response.status
                    if status == 200:
                        response_answer = json.loads(await response.text())
                        if response_answer.get('expires', 0) > int(time.time()):
                            answer = response_answer.get('answer')
                            return await self.make_request(http_client, 'POST', endpoint="/durov/", json=answer)
        return None

    @error_handler
    async def check_proxy(self, http_client: aiohttp.ClientSession) -> None:
        response = await self.make_request(http_client, 'GET', url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
        ip = response.get('origin')
        logger.info(f"{self.session_name} | Proxy IP: {ip}")
    
    #@error_handler
    async def run(self, user_agent) -> None:
                
        proxy_conn = ProxyConnector().from_url(self.proxy) if self.proxy else None
        http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)
        ref_id, init_data = await self.get_tg_web_data()
        
        if not init_data:
            if not http_client.closed:
                await http_client.close()
            if proxy_conn:
                if not proxy_conn.closed:
                    proxy_conn.close()
                    
        if self.proxy:
            await self.check_proxy(http_client=http_client)
            
        http_client.headers['User-Agent'] = user_agent
        
        while True:
            try:
                if http_client.closed:
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()

                    proxy_conn = ProxyConnector().from_url(self.proxy) if self.proxy else None
                    http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)
                    http_client.headers['User-Agent'] = user_agent
                
                user_data = await self.login(http_client=http_client, init_data=init_data, ref_id=ref_id)
                if not user_data:
                    logger.info(f"{self.session_name} | <r>Failed login</r>")
                    sleep_time = randint(*settings.BIG_SLEEP)
                    logger.info(f"{self.session_name} | Sleep <y>{sleep_time}s</y>")
                    await asyncio.sleep(delay=sleep_time)
                    continue
                http_client.headers['Authorization'] = "Bearer " + user_data.get("access_token")
                logger.info(f"{self.session_name} | Login successful")
                user = user_data.get('user')
                squad_id = user.get('squad_id')
                rating = await self.get_detail(http_client=http_client)
                logger.info(f"{self.session_name} | ID: <y>{user.get('id')}</y> | Points : <y>{rating}</y>")
                
                if squad_id is None:
                    await self.join_squad(http_client=http_client)
                    await asyncio.sleep(1)
                    
                data_squad = await self.get_squad(http_client=http_client)
                if data_squad:
                    logger.info(f"{self.session_name} | Squad : <y>{data_squad.get('name')}</y> | Member : <y>{data_squad.get('members_count')}</y> | Ratings : <y>{data_squad.get('rating')}</y>")    
                
                data_visit = await self.visit(http_client=http_client)
                if data_visit:
                    await asyncio.sleep(1)
                    logger.info(f"{self.session_name} | Daily Streak : <y>{data_visit.get('streak')}</y>")
                
                await self.streak(http_client=http_client)
                
                if settings.AUTO_HOLD_COIN:
                    hold_coins = await self.claim_hold_coins(http_client=http_client)
                    if hold_coins:
                        await asyncio.sleep(1)
                        logger.info(f"{self.session_name} | Reward HoldCoins: <y>+{hold_coins}⭐</y>")
                    await asyncio.sleep(10)
                
                if settings.AUTO_SWIPE_COIN:
                    swipe_coins = await self.claim_swipe_coins(http_client=http_client)
                    if swipe_coins:
                        await asyncio.sleep(1)
                        logger.info(f"{self.session_name} | Reward SwipeCoins: <y>+{swipe_coins}⭐</y>")
                    await asyncio.sleep(10)
                
                if settings.AUTO_ROULETTE:
                    roulette = await self.claim_roulette(http_client=http_client)
                    if roulette:
                        await asyncio.sleep(1)
                        logger.info(f"{self.session_name} | Reward Roulette : <y>+{roulette}⭐</y>")
                    await asyncio.sleep(10)
                
                if settings.AUTO_PUZZLE:
                    puzzle = await self.puvel_puzzle(http_client=http_client)
                    if puzzle:
                        await asyncio.sleep(1)
                        logger.info(f"{self.session_name} | Reward Puzzle Pavel: <y>+5000⭐</y>")
                    await asyncio.sleep(10)
                
                if settings.AUTO_TASKS:
                    data_daily = await self.get_daily(http_client=http_client)
                    if data_daily:
                        for daily in reversed(data_daily):
                            await asyncio.sleep(10)
                            id = daily.get('id')
                            title = daily.get('title')
                            type = daily.get('type')
                            #if title not in ["Donate rating", "Boost Major channel", "TON Transaction"]:
                            if id in self.skip_tasks:
                                logger.info(f"{self.session_name} | Skip Daily Task : <y>{title}</y> | {id} | {type}")
                                continue
                            else:
                                data_done = await self.done_tasks(http_client=http_client, task_id=id)
                                if data_done and data_done.get('is_completed') is True:
                                    await asyncio.sleep(1)
                                    logger.info(f"{self.session_name} | Daily Task : <y>{daily.get('title')}</y> | Reward : <y>{daily.get('award')}</y>")
                    
                    data_task = await self.get_tasks(http_client=http_client)
                    if data_task:
                        for task in data_task:
                            await asyncio.sleep(10)
                            id = task.get('id')
                            type = task.get('type')
                            title = task.get('title')
                            if task in self.skip_tasks:
                                logger.info(f"{self.session_name} | Skip Daily Task : <y>{title}</y> | {id} | {type}")
                                continue
                            elif type == 'code':
                                logger.info(f"{self.session_name} | Skip Daily Task : <y>{title}</y> | {id} | {type}")
                                continue
                            elif type == 'subscribe_channel':
                                if not settings.TASKS_WITH_JOIN_CHANNEL:
                                    continue
                                await self.join_and_mute_tg_channel(link=task.get('payload').get('url'))
                                await asyncio.sleep(5)
                            
                            else:
                                data_done = await self.done_tasks(http_client=http_client, task_id=id)
                                if data_done and data_done.get('is_completed') is True:
                                    await asyncio.sleep(1)
                                    logger.info(f"{self.session_name} | Task : <y>{task.get('title')}</y> | Reward : <y>{task.get('award')}</y>")
                await http_client.close()
                if proxy_conn:
                    if not proxy_conn.closed:
                        proxy_conn.close()
            
            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=3)
                
            finally:    
                BIG_SLEEP = randint(*settings.BIG_SLEEP)
                logger.info(f"{self.session_name} | Sleep <y>{BIG_SLEEP}s</y>")
                await asyncio.sleep(delay=BIG_SLEEP)    
            
        

async def run_tapper(tg_client: Client, user_agent: str, proxy: str | None):
    try:
        if not settings.ACCOUNTS_MOOD_SEQUENTIAL:
            _sleep = randint(*settings.LOGIN_SLEEP)
            logger.info(f"{tg_client.name:<10} | Bot will start in {_sleep}s ...")
            await asyncio.sleep(_sleep)
            await Tapper(tg_client=tg_client, proxy=proxy).run(user_agent=user_agent)
        else:
            await Tapper(tg_client=tg_client, proxy=proxy).run(user_agent=user_agent)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")


















