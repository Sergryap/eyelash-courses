from django.conf import settings
from django.core.management import BaseCommand
from vk_bot.vk_bot import VkBot


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_vk_bot()
        except Exception as exc:
            print(exc)
            raise


def start_vk_bot():
    bot = VkBot(settings.VK_TOKEN, settings.VK_GROUP_ID)
    bot.updater.run_forever()
