from asgiref.sync import sync_to_async
from vkwave.bots import (
    SimpleBotEvent,
    SimpleLongPollBot,
    DefaultRouter,
    simple_bot_message_handler,
)
from vkwave.bots.storage.types import Key
from vkwave.bots.storage.storages import Storage

from courses.models import Client
from .mat_filter import MatFilter

storage = Storage()


async def start(event: SimpleBotEvent):
    user_id = event.user_id
    msg = event.text.strip()
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    await event.answer(message=msg)

    return 'START'


class VkDialogBot:

    client_router = DefaultRouter()
    states_functions = {
        'START': start,
    }

    def __init__(self, token, group_id):

        self.token = token
        self.group_id = group_id
        self.updater = SimpleLongPollBot(tokens=token, group_id=group_id)
        self.updater.dispatcher.add_router(self.client_router)

    @staticmethod
    @simple_bot_message_handler(client_router, MatFilter())
    async def basic_send(event: SimpleBotEvent):
        await VkDialogBot.handle_users_reply(event)

    @classmethod
    async def handle_users_reply(cls, event: SimpleBotEvent):
        user_id = event.user_id
        api = event.api_ctx

        if not await storage.contains(Key(f'{user_id}_first_name')):
            user_data = (await api.users.get(user_ids=user_id)).response[0]
            await storage.put(Key(f'{user_id}_first_name'), user_data.first_name)
            await storage.put(Key(f'{user_id}_last_name'), user_data.last_name)

        user, _ = await Client.objects.aget_or_create(
            vk_id=user_id,
            defaults={
                'first_name': await storage.get(Key(f'{user_id}_first_name')),
                'last_name': await storage.get(Key(f'{user_id}_last_name')),
                'vk_profile': f'https://vk.com/id{user_id}'
            }
        )

        if event.text.lower().strip() in ['start', '/start', 'начать', 'старт']:
            user_state = 'START'
        else:
            user_state = user.bot_state

        state_handler = cls.states_functions[user_state]
        user.bot_state = await state_handler(event)
        await sync_to_async(user.save)()
