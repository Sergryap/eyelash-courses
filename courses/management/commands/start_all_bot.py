import logging
import asyncio

from django.conf import settings
from django.core.management import BaseCommand

from vk_bot.async_longpoll import event_handler as vk_event_handler
from tg_bot.tg_bot import handle_event as tg_event_handler
from vk_bot.vklongpollserver import VkLongPollServer
from tg_bot.tglongpollserver import TgLongPollServer
from tg_bot.tg_api import TgApi
from vk_bot.vk_api import VkApi


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

    vk_api = VkApi(
        vk_group_token=settings.VK_TOKEN,
        redis_db=settings.REDIS_DB,
    )
    vk_connect = VkLongPollServer(
        api=vk_api,
        group_id=settings.VK_GROUP_ID,
        handle_event=vk_event_handler
    )
    tg_api = TgApi(
        tg_token=settings.TG_TOKEN,
        redis_db=settings.REDIS_DB,
    )
    tg_connect = TgLongPollServer(
        api=tg_api,
        handle_event=tg_event_handler
    )

    loop = asyncio.get_event_loop()
    for connect in [vk_connect, tg_connect]:
        asyncio.ensure_future(connect.listen_server())
    loop.run_forever()
