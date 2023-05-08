import asyncio
import aiohttp
import logging
import json
import redis
from aiohttp import client_exceptions
from time import sleep

logger = logging.getLogger('telegram')


class TgLongPollServer:

    def __init__(self, tg_token: str, redis_db: redis.Redis, handle_event: callable):
        self.token = tg_token
        self.redis_db = redis_db
        self.handle_event = handle_event
        self.url = f'https://api.telegram.org/bot{tg_token}/getUpdates'
        self.params = {'timeout': 25, 'limit': 1}

    @staticmethod
    async def get_cleaned_event(event):
        if event.get('message'):
            event_info = event['message']
            return {
                'user_reply': event_info['text'],
                'chat_id': event_info['chat']['id'],
                'first_name': event_info['chat']['first_name'],
                'last_name': event_info['chat'].get('last_name', ''),
                'username': event_info['chat'].get('username', ''),
                'message_id': event_info['message_id'],
                'message': True
            }
        elif event.get('callback_query'):
            event_info = event['callback_query']
            return {
                'user_reply': event_info['data'],
                'chat_id': event_info['message']['chat']['id'],
                'first_name': event_info['message']['chat']['first_name'],
                'last_name': event_info['message']['chat'].get('last_name', ''),
                'username': event_info['message']['chat'].get('username', ''),
                'callback_query_id': event_info['id'],
                'message_id': event_info['message']['message_id'],
                'callback_query': True
            }
        # elif
        # При необходимости добавить новые типы событий
        # return
        return

    async def listen_server(self):
        async with aiohttp.ClientSession() as session:
            connect = {'session': session, 'token': self.token, 'redis_db': self.redis_db}
            while True:
                try:
                    await asyncio.sleep(0.1)
                    async with session.get(self.url, params=self.params) as res:
                        res.raise_for_status()
                        updates = json.loads(await res.text())
                    if not updates.get('result') or not updates['ok']:
                        continue
                    update = updates['result'][-1]
                    self.params['offset'] = update['update_id'] + 1
                    event = await self.get_cleaned_event(update)
                    if not event:
                        continue
                    await self.handle_event(connect, event)
                except ConnectionError:
                    sleep(5)
                    logger.warning(f'Соединение было прервано', stack_info=True)
                    continue
                except client_exceptions.ClientResponseError as err:
                    sleep(1)
                    logger.exception(err)
                except client_exceptions.ServerTimeoutError:
                    logger.warning(f'Ошибка ReadTimeout', stack_info=True)
                    continue
                except Exception as err:
                    logger.exception(err)
                    print(err)
