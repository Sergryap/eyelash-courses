import aiohttp
import asyncio
import logging
import json
from aiohttp import client_exceptions
from abc import ABC, abstractmethod
from .vk_bot import VkApi
from .tg_bot import TgApi

logger = logging.getLogger('telegram')


class LongPollServer(ABC):

    @abstractmethod
    def __init__(self, api: TgApi | VkApi, handle_event: callable):
        self.api = api
        self.handle_event = handle_event
        self.first_connect = True
        self.start = True

    async def insert_handle_event_task(self, event, *, loop=None):
        async def additional_coro():
            await self.handle_event(self.api, event)
        asyncio.ensure_future(additional_coro(), loop=loop)

    @abstractmethod
    async def listen_server(self, *, loop=None):
        pass


class StartAsyncSession:
    def __init__(self, instance: LongPollServer):
        self.instance = instance

    async def __aenter__(self):
        self.instance.api.session = aiohttp.ClientSession()
        return self.instance.api.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.instance.api.session.close()


class UpdateVkEventSession:

    """Класс контекстного менеджера для получения события VK"""

    url = 'https://api.vk.com/method/groups.getLongPollServer'

    def __init__(self, instance):
        self.instance = instance

    async def __aenter__(self):
        if self.instance.start:
            self.instance.key, self.instance.server, self.instance.ts = await self.get_params()
            self.instance.start = False
            self.instance.get_params = self.get_params
        params = {'act': 'a_check', 'key': self.instance.key, 'ts': self.instance.ts, 'wait': 25}
        response = await self.instance.api.session.get(self.instance.server, params=params)
        response.raise_for_status()
        return json.loads(await response.text())

    async def get_params(self):
        async with self.instance.api.session.get(self.url, params=self.instance.vk_api_params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
        key = response['response']['key']
        server = response['response']['server']
        ts = response['response']['ts']
        return key, server, ts

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, ConnectionError):
            t = 0 if self.instance.first_connect else 5
            self.instance.first_connect = False
            await asyncio.sleep(t)
            logger.warning(f'Соединение было прервано: {exc_val}', stack_info=True)
            self.instance.key, self.instance.server, self.instance.ts = (
                await self.get_params()
            )
            return True
        if isinstance(exc_val, client_exceptions.ServerTimeoutError):
            logger.warning(f'Ошибка ReadTimeout: {exc_val}', stack_info=True)
            self.instance.key, self.instance.server, self.instance.ts = (
                await self.get_params()
            )
            return True
        if isinstance(exc_val, Exception):
            logger.exception(exc_val)
            self.instance.key, self.instance.server, self.instance.ts = (
                await self.get_params()
            )
            self.instance.first_connect = True
            return True


class UpdateTgEventSession:

    """Класс контекстного менеджера для получения события TG"""

    def __init__(self, instance):
        self.instance = instance

    async def __aenter__(self):
        response = await self.instance.api.session.get(self.instance.url, params=self.instance.params)
        response.raise_for_status()
        return json.loads(await response.text())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, ConnectionError):
            t = 0 if self.instance.first_connect else 5
            self.instance.first_connect = False
            await asyncio.sleep(t)
            logger.warning(f'Соединение было прервано: {exc_val}', stack_info=True)
            return True
        if isinstance(exc_val, client_exceptions.ServerTimeoutError):
            logger.warning(f'Ошибка ReadTimeout: {exc_val}', stack_info=True)
            return True
        if isinstance(exc_val, Exception):
            logger.exception(exc_val)
            self.instance.first_connect = True
            return True
