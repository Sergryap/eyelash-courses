import logging
import asyncio

from django.conf import settings
from django.core.management import BaseCommand
from vk_bot.async_longpoll import listen_server
from vk_bot.logger import MyLogsHandler


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_vk_bot()
        except Exception as exc:
            print(exc)
            raise


def start_vk_bot():
    logger = logging.getLogger('telegram')
    logger.setLevel(logging.WARNING)
    logger.addHandler(MyLogsHandler(settings.TG_LOGGER_BOT, settings.TG_LOGGER_CHAT))
    logger.warning('Бот "eyelash-courses" запущен')

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(listen_server())
    loop.run_forever()
