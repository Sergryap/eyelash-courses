import logging
import asyncio

from django.core.management import BaseCommand
from tg_bot.tg_bot import listen_server


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

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(listen_server())
    loop.run_forever()
