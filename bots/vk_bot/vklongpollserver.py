import logging
from typing import Callable, Awaitable
from pydantic import ValidationError

from .vk_api import VkApi
from bots.general import LongPollServer, StartAsyncSession, UpdateVkEventSession
from . import vk_types

logger = logging.getLogger('telegram')


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

    async def listen_server(self, *, loop=None):
        async with StartAsyncSession(self):
            await self.api.create_tasks_from_db(hour_interval=2, minute_offset=10)
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
                            params.key, __, __ = await self.get_params()
                        elif update.failed == 3:
                            params.key, __, params.ts = await self.get_params()
                        continue
                    await self.api.update_course_tasks_triggered_admin('update_vk_tasks')
                    await self.api.create_message_tasks('vk_create_message')
                    params.ts = update.ts
                    for event in update.updates:
                        if event.type != 'message_new':
                            continue
                        msg_event = vk_types.NewMessageUpdate.parse_obj(event).object.message
                        await self.insert_handle_event_task(msg_event, loop=loop)
