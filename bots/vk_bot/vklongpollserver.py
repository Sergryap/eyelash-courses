import asyncio
import logging

from typing import Callable, Awaitable
from pydantic import ValidationError
from aiohttp import client_exceptions
from .vk_api import VkApi
from bots.general import LongPollServer, StartAsyncSession
from . import vk_types

logger = logging.getLogger('telegram')


class UpdateVkEventSession:
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


class VkLongPollServer(LongPollServer):
    """Класс для получения событий от сервера Vk и отправки их в главный обработчик событий handle_event"""

    url = 'https://api.vk.com/method/groups.getLongPollServer'

    def __init__(
            self,
            api: VkApi,
            group_id: int,
            handle_event: Callable[[VkApi, vk_types.Message], Awaitable[None]]
    ):
        super().__init__(api, handle_event)
        self.vk_api_params = vk_types.VkApiParams(access_token=api.token, group_id=group_id).dict()

    async def get_params(self):
        async with self.api.session.get(self.url, params=self.vk_api_params) as res:
            res.raise_for_status()
            response = vk_types.ServerResponse.parse_raw(await res.text())
        return response.response

    async def init_tasks(self):
        await self.api.create_tasks_from_db(hour_interval=2, minute_offset=10)

    async def update_event(self, loop=None):
        while True:
            async with UpdateVkEventSession(self):
                if self.start:
                    params = await self.get_params()
                    self.start = False
                response = await self.api.session.get(params.server, params=params.dict(exclude={'server'}))
                response.raise_for_status()
                try:
                    update = vk_types.ServerUpdates.parse_raw(await response.text())
                except ValidationError:
                    update = vk_types.ServerFailedUpdate.parse_raw(await response.text())
                    if update.failed == 1:
                        params.ts = update.ts
                    elif update.failed == 2:
                        res = await self.get_params()
                        params.key = res.key
                    elif update.failed == 3:
                        res = await self.get_params()
                        params.key, params.ts = res.key, res.ts
                    continue
                await self.api.update_course_tasks_triggered_admin('update_vk_tasks')
                await self.api.create_message_tasks('vk_create_message')
                params.ts = update.ts
                for event in update.updates:
                    if event.type != 'message_new':
                        continue
                    msg_event = vk_types.NewMessageUpdate.parse_obj(event).object.message
                    await self.insert_handle_event_task(msg_event, loop=loop)
