import logging
import asyncio

from django.core.management import BaseCommand
from django.conf import settings
from bots import tg_event_handler, TgLongPollServer, TgApi


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
        handle_event=tg_event_handler
    )

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(connect.listen_server())
    loop.run_forever()
