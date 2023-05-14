import logging
import json
import asyncio
from .tg_api import TgApi, TgEvent
from bots.general import LongPollServer, StartAsyncSession, UpdateTgEventSession

logger = logging.getLogger('telegram')


class TgLongPollServer(LongPollServer):
    """Класс для получения событий от сервера Tg и отправки их в главный обработчик событий handle_event"""

    def __init__(self, api: TgApi, handle_event: callable):
        super().__init__(api, handle_event)
        self.url = f'https://api.telegram.org/bot{api.token}/getUpdates'
        self.params = {'timeout': 25, 'limit': 1}

    async def listen_server(self):
        async with StartAsyncSession(self):
            while True:
                async with UpdateTgEventSession(self) as response:
                    updates = json.loads(await response.text())
                if not updates.get('result') or not updates['ok']:
                    continue
                update = updates['result'][-1]
                self.params['offset'] = update['update_id'] + 1
                event = TgEvent(update)
                if hasattr(event, 'unknown_event'):
                    continue

                async def coro():
                    await self.handle_event(self.api, event)
                asyncio.ensure_future(coro())
