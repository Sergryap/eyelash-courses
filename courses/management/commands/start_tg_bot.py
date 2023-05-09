import logging
import asyncio

from django.core.management import BaseCommand
from tg_bot.tg_bot import handle_event
from tg_bot.tglongpollserver import TgLongPollServer
from django.conf import settings
from tg_bot.tg_api import TgApi


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_tg_bot()
        except Exception as exc:
            print(exc)
            raise


def start_tg_bot():
    logger = logging.getLogger('telegram')
    logger.warning('TG-Бот "eyelash-courses" запущен')

    api = TgApi(
        tg_token=settings.TG_TOKEN,
        redis_db=settings.REDIS_DB,
    )
    connect = TgLongPollServer(
        api=api,
        handle_event=handle_event
    )

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(connect.listen_server())
    loop.run_forever()
