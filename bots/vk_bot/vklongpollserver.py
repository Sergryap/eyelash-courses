import logging
import json
import asyncio
from .vk_api import VkApi
from bots.general import LongPollServer, StartAsyncSession, UpdateVkEventSession

logger = logging.getLogger('telegram')


class VkLongPollServer(LongPollServer):

    url = 'https://api.vk.com/method/groups.getLongPollServer'

    def __init__(self, api: VkApi, group_id: int, handle_event: callable):
        super().__init__(api, handle_event)
        self.vk_api_params = {'access_token': api.token, 'v': '5.131', 'group_id': group_id}

    async def listen_server(self):
        async with StartAsyncSession(self):
            while True:
                async with UpdateVkEventSession(self) as response:
                    updates = json.loads(await response.text())
                if 'failed' in updates:
                    if updates['failed'] == 1:
                        self.ts = updates['ts']
                    elif updates['failed'] == 2:
                        self.key, __, __ = await self.get_params()
                    elif updates['failed'] == 3:
                        self.key, __, self.ts = await self.get_params()
                    continue
                self.ts = updates['ts']
                for event in updates['updates']:
                    if event['type'] != 'message_new':
                        continue

                    async def coro():
                        await self.handle_event(self.api, event)
                    asyncio.ensure_future(coro())
