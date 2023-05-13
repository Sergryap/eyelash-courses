import aiohttp
import logging
import json
from aiohttp import client_exceptions
from time import sleep
from .vk_api import VkApi
from bots.general import LongPollServer, StartAsyncSession, VkEvent

logger = logging.getLogger('telegram')


class VkLongPollServer(LongPollServer):

    url = 'https://api.vk.com/method/groups.getLongPollServer'

    def __init__(self, api: VkApi, group_id: int, handle_event: callable):
        super().__init__(api, handle_event)
        self.vk_api_params = {'access_token': api.token, 'v': '5.131', 'group_id': group_id}

    async def get_long_poll_server(self, session: aiohttp.ClientSession):
        async with session.get(self.url, params=self.vk_api_params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
        key = response['response']['key']
        server = response['response']['server']
        ts = response['response']['ts']
        return key, server, ts

    async def listen_server_old(self):
        async with StartAsyncSession(self) as session:
            key, server, ts = await self.get_long_poll_server(session)
            while True:
                try:
                    params = {'act': 'a_check', 'key': key, 'ts': ts, 'wait': 25}
                    async with session.get(server, params=params) as res:
                        res.raise_for_status()
                        response = json.loads(await res.text())
                    if 'failed' in response:
                        if response['failed'] == 1:
                            ts = response['ts']
                        elif response['failed'] == 2:
                            key, __, __ = await self.get_long_poll_server(session)
                        elif response['failed'] == 3:
                            key, __, ts = await self.get_long_poll_server(session)
                        continue
                    ts = response['ts']
                    for event in response['updates']:
                        if event['type'] != 'message_new':
                            continue
                        await self.handle_event(self.api, event)
                except ConnectionError as err:
                    t = 0 if self.first_connect else 5
                    self.first_connect = False
                    sleep(t)
                    logger.warning(f'Соединение было прервано: {err}', stack_info=True)
                    key, server, ts = await self.get_long_poll_server(session)
                    continue
                except client_exceptions.ServerTimeoutError as err:
                    logger.warning(f'Ошибка ReadTimeout: {err}', stack_info=True)
                    key, server, ts = await self.get_long_poll_server(session)
                    continue
                except Exception as err:
                    logger.exception(err)
                    key, server, ts = await self.get_long_poll_server(session)
                    self.first_connect = True

    async def listen_server(self):
        async with StartAsyncSession(self):
            while True:
                async with VkEvent(self) as res:
                    res.raise_for_status()
                    response = json.loads(await res.text())
                if 'failed' in response:
                    if response['failed'] == 1:
                        self.ts = response['ts']
                    elif response['failed'] == 2:
                        self.key, __, __ = await self.get_params()
                    elif response['failed'] == 3:
                        self.key, __, self.ts = await self.get_params()
                    continue
                self.ts = response['ts']
                for event in response['updates']:
                    if event['type'] != 'message_new':
                        continue
                    await self.handle_event(self.api, event)
