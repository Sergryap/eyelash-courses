import aiohttp
import asyncio
import logging

from aiohttp import client_exceptions
from abc import ABC, abstractmethod
from typing import Callable, Awaitable
from .vk_bot import VkApi, vk_types
from .tg_bot import TgApi, tg_types

logger = logging.getLogger('telegram')


class UpdateEventSession:
    """Класс контекстного менеджера для получения события VK"""

    def __init__(self, instance):
        self.instance = instance

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.instance.start = True
        if isinstance(exc_val, ConnectionError):
            t = 0 if self.instance.first_connect else 5
            self.instance.first_connect = False
            await asyncio.sleep(t)
            logger.warning(f'Соединение было прервано: {exc_val}', stack_info=True)
            return True
        if isinstance(exc_val, client_exceptions.ServerTimeoutError):
            logger.warning(f'Ошибка ReadTimeout: {exc_val}', stack_info=True)
            return True
        if isinstance(exc_val, client_exceptions.ClientResponseError):
            logger.warning(f'Ошибка ClientResponseError: {exc_val}', stack_info=True)
            self.instance.start = True
            return True
        if isinstance(exc_val, Exception):
            logger.exception(exc_val)
            self.instance.first_connect = True
            return True


class LongPollServer(ABC):

    @abstractmethod
    def __init__(
            self,
            api: TgApi | VkApi,
            handle_event: Callable[[VkApi | TgApi, vk_types.Message | tg_types.Update], Awaitable[None]],
    ):
        self.api = api
        self.handle_event = handle_event
        self.first_connect = True
        self.start = True

    async def insert_handle_event_task(
            self,
            event: vk_types.NewMessage | tg_types.Update,
            *,
            loop=None
    ) -> Awaitable[None]:
        async def additional_coro():
            await self.handle_event(self.api, event)
        asyncio.ensure_future(additional_coro(), loop=loop)

    @abstractmethod
    async def init_tasks(self):
        pass

    @abstractmethod
    async def update_tasks(self):
        pass

    @abstractmethod
    async def get_event(self, loop=None) -> Awaitable[tg_types.Update | vk_types.NewMessageUpdate | None]:
        pass

    async def listen_server(self, *, loop=None) -> Awaitable[None]:
        async with StartAsyncSession(self):
            await self.init_tasks()
            while True:
                async with UpdateEventSession(self):
                    event = await self.get_event(loop)
                    await self.update_tasks()
                    if not event:
                        continue
                    asyncio.ensure_future(self.handle_event(self.api, event), loop=loop)


class StartAsyncSession:
    def __init__(self, instance: LongPollServer):
        self.instance = instance

    async def __aenter__(self):
        self.instance.api.session = aiohttp.ClientSession()
        # Обновляем список отложенных задач по отправке оповещений
        await self.instance.api.update_message_sending_tasks()
        return self.instance.api.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.instance.api.session.close()
