import asyncio
import aiohttp
import logging
import json
import redis
from aiohttp import client_exceptions
from time import sleep

logger = logging.getLogger('telegram')


class LongPollServer:
    def __init__(self, vk_group_token: str, redis_db: redis.Redis, group_id: int, handle_event: callable):
        self.token = vk_group_token
        self.redis_db = redis_db
        self.group_id = group_id
        self.handle_event = handle_event
        self.vk_api_params = {'access_token': vk_group_token, 'v': '5.131', 'group_id': group_id}
        self.url = 'https://api.vk.com/method/groups.getLongPollServer'

    async def get_long_poll_server(self, session: aiohttp.ClientSession):
        async with session.get(self.url, params=self.vk_api_params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
            key = response['response']['key']
            server = response['response']['server']
            ts = response['response']['ts']
            return key, server, ts

    async def listen_server(self):
        async with aiohttp.ClientSession() as session:
            key, server, ts = await self.get_long_poll_server(session)
            connect = {'session': session, 'token': self.token, 'redis_db': self.redis_db}
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
                        await asyncio.sleep(0.2)
                        await self.handle_event(connect, event)
                except ConnectionError as err:
                    sleep(5)
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
