import logging
import asyncio

from django.core.management import BaseCommand
from vk_bot.async_longpoll import event_handler
from vk_bot.longpollserver import LongPollServer
from vk_bot.vk_api import VkApi
from django.conf import settings


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

    api = VkApi(
        vk_group_token=settings.VK_TOKEN,
        redis_db=settings.REDIS_DB,
    )

    connect = LongPollServer(
        api=api,
        group_id=settings.VK_GROUP_ID,
        handle_event=event_handler
    )

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(connect.listen_server())
    loop.run_forever()
