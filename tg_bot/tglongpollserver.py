import logging
import json
from aiohttp import client_exceptions
from time import sleep
from tg_bot.tg_api import TgApi
from courses.general_functions import LongPollServer, StartAsyncSession

logger = logging.getLogger('telegram')


class TgLongPollServer(LongPollServer):
    """Класс для получения событий от сервера Tg и отправки их в главный обработчик событий handle_event"""

    def __init__(self, api: TgApi, handle_event: callable):
        super().__init__(api, handle_event)
        self.url = f'https://api.telegram.org/bot{api.token}/getUpdates'
        self.params = {'timeout': 25, 'limit': 1}

    @staticmethod
    async def get_cleaned_event(event):
        if event.get('message'):
            event_info = event['message']
            chat_event_info = event_info['chat']
            return {
                'user_reply': event_info['text'],
                'chat_id': chat_event_info['id'],
                'first_name': chat_event_info['first_name'],
                'last_name': chat_event_info.get('last_name', ''),
                'username': chat_event_info.get('username', ''),
                'message_id': event_info['message_id'],
                'message': True
            }
        elif event.get('callback_query'):
            event_info = event['callback_query']
            chat_event_info = event_info['message']['chat']
            return {
                'user_reply': event_info['data'],
                'chat_id': chat_event_info['id'],
                'first_name': chat_event_info['first_name'],
                'last_name': chat_event_info.get('last_name', ''),
                'username': chat_event_info.get('username', ''),
                'callback_query_id': event_info['id'],
                'message_id': event_info['message']['message_id'],
                'callback_query': True
            }
        # elif
        # При необходимости добавить новые типы событий
        # return
        return

    async def listen_server(self):
        async with StartAsyncSession(self) as session:
            while True:
                try:
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
                    t = 0 if self.first_connect else 5
                    self.first_connect = False
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
                    self.first_connect = True
