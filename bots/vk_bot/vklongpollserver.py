import logging
import json
from .vk_api import VkApi
from bots.general import LongPollServer, StartAsyncSession, UpdateVkEventSession

logger = logging.getLogger('telegram')


class VkLongPollServer(LongPollServer):
    """Класс для получения событий от сервера Vk и отправки их в главный обработчик событий handle_event"""

    url = 'https://api.vk.com/method/groups.getLongPollServer'

    def __init__(self, api: VkApi, group_id: int, handle_event: callable):
        super().__init__(api, handle_event)
        self.vk_api_params = {'access_token': api.token, 'v': '5.131', 'group_id': group_id}

    async def get_params(self):
        async with self.api.session.get(self.url, params=self.vk_api_params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
        key = response['response']['key']
        server = response['response']['server']
        ts = response['response']['ts']
        return key, server, ts

    async def listen_server(self, *, loop=None):
        params = {'act': 'a_check', 'key': None, 'ts': None, 'wait': 25}
        async with StartAsyncSession(self):
            while True:
                async with UpdateVkEventSession(self):
                    if self.start:
                        params['key'], server, params['ts'] = await self.get_params()
                        self.start = False
                    response = await self.api.session.get(server, params=params)
                    response.raise_for_status()
                    updates = json.loads(await response.text())
                    if 'failed' in updates:
                        if updates['failed'] == 1:
                            params['ts'] = updates['ts']
                        elif updates['failed'] == 2:
                            params['key'], __, __ = await self.get_params()
                        elif updates['failed'] == 3:
                            params['key'], __, params['ts'] = await self.get_params()
                        continue
                    params['ts'] = updates['ts']
                    for event in updates['updates']:
                        if event['type'] != 'message_new':
                            continue
                        await self.insert_handle_event_task(event, loop=loop)
