import logging
import asyncio

from django.core.management import BaseCommand
from vk_bot.async_longpoll import listen_server as vk_listen_server
from tg_bot.tg_bot import listen_server as tg_listen_server


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_vk_bot()
        except Exception as exc:
            print(exc)
            raise


def start_vk_bot():
    logger = logging.getLogger('telegram')
    logger.warning('Боты VK и TG "eyelash-courses" запущены')

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(vk_listen_server())
    asyncio.ensure_future(tg_listen_server())
    loop.run_forever()
