from django.conf import settings
from django.core.management import BaseCommand
from vk_bot.vk_bot import VkBot
from vk_bot.mat_filter import MatFilter
from vkwave.bots import SimpleBotEvent, DefaultRouter, simple_bot_message_handler


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_vk_bot()
        except Exception as exc:
            print(exc)
            raise


def start_vk_bot():

    router = DefaultRouter()
    bot = VkBot(settings.VK_TOKEN, settings.VK_GROUP_ID)

    @simple_bot_message_handler(router, MatFilter())
    async def basic_send(event: SimpleBotEvent):
        await bot.handle_users_reply(event)

    bot.updater.dispatcher.add_router(router)
    bot.updater.run_forever()
