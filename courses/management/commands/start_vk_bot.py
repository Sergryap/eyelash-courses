from django.conf import settings
from django.core.management import BaseCommand
from vk_bot.vk_bot import handle_users_reply
from vk_bot.mat_filter import MatFilter
from vkwave.bots import SimpleBotEvent,  SimpleLongPollBot, DefaultRouter, simple_bot_message_handler


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_vk_bot()
        except Exception as exc:
            print(exc)
            raise


def start_vk_bot():

    router = DefaultRouter()

    @simple_bot_message_handler(router, MatFilter())
    async def basic_send(event: SimpleBotEvent):
        await handle_users_reply(event)

    updater = SimpleLongPollBot(tokens=settings.VK_TOKEN, group_id=settings.VK_GROUP_ID)
    updater.dispatcher.add_router(router)
    updater.run_forever()
