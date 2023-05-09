import asyncio
import aiohttp
import logging
import json
from aiohttp import client_exceptions
from time import sleep
from tg_bot.tg_api import TgApi

logger = logging.getLogger('telegram')


class TgLongPollServer:
    """Класс для получения событий от сервера Tg и отправки их в главный обработчик событий handle_event"""

    def __init__(self, api: TgApi, handle_event: callable):
        self.api = api
        self.handle_event = handle_event
        self.url = f'https://api.telegram.org/bot{api.token}/getUpdates'
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
            self.api.session = session
            first_connect = True
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
                    await self.handle_event(self.api, event)
                except ConnectionError:
                    t = 0 if first_connect else 5
                    first_connect = False
                    sleep(t)
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
