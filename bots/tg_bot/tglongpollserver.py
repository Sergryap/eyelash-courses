import logging

from typing import Callable, Awaitable
from . import tg_types
from .tg_api import TgApi
from bots.general import LongPollServer

logger = logging.getLogger('telegram')


class TgLongPollServer(LongPollServer):
    """Класс для получения событий от сервера Tg и отправки их в главный обработчик событий handle_event"""

    def __init__(
            self,
            api: TgApi,
            handle_event: Callable[[TgApi, tg_types.Update], Awaitable[None]],
    ):
        super().__init__(api, handle_event)
        self.url = f'https://api.telegram.org/bot{api.token}/getUpdates'
        self.params = {'timeout': 25, 'limit': 1}

    async def init_tasks(self):
        await self.api.create_tasks_from_db(hour_interval=2)
        await self.api.bypass_users_to_create_tasks(hour_interval=8)

    async def update_tasks(self):
        await self.api.update_course_tasks_triggered_admin('update_tg_tasks')
        await self.api.create_message_tasks('tg_create_message')

    async def get_event(self, loop=None) -> Awaitable[tg_types.Update | None]:
        response = await self.api.session.get(self.url, params=self.params)
        response.raise_for_status()
        updates = tg_types.Response.parse_raw(await response.text())
        if not updates.result or not updates.ok:
            return
        update = updates.result[-1]
        self.params['offset'] = update.update_id + 1
        if not update.message and not update.callback_query:
            return
        return tg_types.Update.parse_obj(update)
