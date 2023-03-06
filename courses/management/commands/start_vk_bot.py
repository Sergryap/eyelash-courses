from django.conf import settings
from django.core.management import BaseCommand
from vk_bot.vk_bot import VkBot
from vk_bot.mat_filter import MatFilter
from vkwave.bots import SimpleBotEvent, DefaultRouter, simple_bot_message_handler
from vk_bot import handlers
from vkwave.bots.storage.storages import Storage


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_vk_bot()
        except Exception as exc:
            print(exc)
            raise


def start_vk_bot():
    states_functions = {
        'START': handlers.start,
    }
    storage = Storage()
    router = DefaultRouter()
    bot = VkBot(
        settings.VK_TOKEN,
        settings.VK_GROUP_ID,
        router,
        states_functions,
        storage
    )

    @simple_bot_message_handler(router, MatFilter())
    async def basic_send(event: SimpleBotEvent):
        await bot.handle_users_reply(event)

    bot.updater.run_forever()
