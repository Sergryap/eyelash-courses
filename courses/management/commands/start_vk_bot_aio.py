import logging
import asyncio

from django.core.management import BaseCommand
from vk_bot.async_longpoll import listen_server


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_vk_bot()
        except Exception as exc:
            print(exc)
            raise


def start_vk_bot():
    logger = logging.getLogger('telegram')
    logger.warning('VK-Бот "eyelash-courses" запущен')

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(listen_server())
    loop.run_forever()
