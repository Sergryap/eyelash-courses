import logging
import asyncio

from django.conf import settings
from django.core.management import BaseCommand

from bots import TgLongPollServer, VkLongPollServer, TgApi, VkApi, tg_event_handler, vk_event_handler


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_all_bots()
        except Exception as exc:
            print(exc)
            raise


async def get_bot_tasks(vk_connect, tg_connect):
    tasks = []
    for connect in [vk_connect, tg_connect]:
        tasks.append(asyncio.ensure_future(connect.listen_server()))
    await asyncio.gather(*tasks, return_exceptions=True)


def start_all_bots():
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

    asyncio.run(get_bot_tasks(vk_connect, tg_connect))

    # loop = asyncio.get_event_loop()
    # for connect in [vk_connect, tg_connect]:
    #     asyncio.ensure_future(connect.listen_server())
    # loop.run_forever()
