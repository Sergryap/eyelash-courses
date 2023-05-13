import logging
import asyncio

from django.core.management import BaseCommand
from django.conf import settings
from bots import vk_event_handler, VkLongPollServer, VkApi


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

    connect = VkLongPollServer(
        api=api,
        group_id=settings.VK_GROUP_ID,
        handle_event=vk_event_handler
    )

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(connect.listen_server())
    loop.run_forever()
