import aiohttp
import asyncio
import logging

from abc import ABC, abstractmethod
from typing import Callable, Awaitable
from .vk_bot import VkApi, vk_types
from .tg_bot import TgApi, tg_types

logger = logging.getLogger('telegram')


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
    async def update_event(self, loop=None):
        pass

    async def listen_server(self, *, loop=None) -> Awaitable[None]:
        async with StartAsyncSession(self):
            await self.init_tasks()
            await self.update_event(loop)


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
