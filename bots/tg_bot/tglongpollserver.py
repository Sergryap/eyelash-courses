import asyncio
import logging

from aiohttp import client_exceptions
from typing import Callable, Awaitable
from . import tg_types
from .tg_api import TgApi
from bots.general import LongPollServer, StartAsyncSession

logger = logging.getLogger('telegram')


class UpdateTgEventSession:

    """Класс контекстного менеджера для получения события TG"""

    def __init__(self, instance):
        self.instance = instance

    async def __aenter__(self):
        return self

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
        if isinstance(exc_val, client_exceptions.ClientResponseError):
            logger.warning(f'Ошибка ClientResponseError: {exc_val}', stack_info=True)
            return True
        if isinstance(exc_val, Exception):
            logger.exception(exc_val)
            self.instance.first_connect = True
            return True


class TgLongPollServer(LongPollServer):
    """Класс для получения событий от сервера Tg и отправки их в главный обработчик событий handle_event"""

    def __init__(
            self,
            api: TgApi,
            handle_event: Callable[[TgApi, tg_types.Update], Awaitable[None]]
    ):
        super().__init__(api, handle_event)
        self.url = f'https://api.telegram.org/bot{api.token}/getUpdates'
        self.params = {'timeout': 25, 'limit': 1}

    async def listen_server(self, *, loop=None) -> Awaitable[None]:
        async with StartAsyncSession(self):
            await self.api.create_tasks_from_db(hour_interval=2)
            await self.api.bypass_users_to_create_tasks(hour_interval=8)
            while True:
                async with UpdateTgEventSession(self):
                    response = await self.api.session.get(self.url, params=self.params)
                    response.raise_for_status()
                    updates = tg_types.Response.parse_raw(await response.text())
                    await self.api.update_course_tasks_triggered_admin('update_tg_tasks')
                    await self.api.create_message_tasks('tg_create_message')
                    if not updates.result or not updates.ok:
                        continue
                    update = updates.result[-1]
                    self.params['offset'] = update.update_id + 1
                    event = tg_types.Update.parse_obj(update)
                    if not update.message and not update.callback_query:
                        continue
                    await self.insert_handle_event_task(event, loop=loop)
