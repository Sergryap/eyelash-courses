from asgiref.sync import sync_to_async
from vkwave.bots import SimpleBotEvent, SimpleLongPollBot
from vkwave.bots.storage.types import Key
from vkwave.bots.storage.storages import Storage
from courses.models import Client
from vk_bot import handlers


class VkBot:

    storage = Storage()
    states_functions = {
        'START': handlers.start,
    }

    def __init__(self, token, group_id):
        self.updater = SimpleLongPollBot(tokens=token, group_id=group_id)

    @classmethod
    async def handle_users_reply(cls, event: SimpleBotEvent):
        user_id = event.user_id
        api = event.api_ctx

        if not await cls.storage.contains(Key(f'{user_id}_first_name')):
            user_data = (await api.users.get(user_ids=user_id)).response[0]
            await cls.storage.put(Key(f'{user_id}_first_name'), user_data.first_name)
            await cls.storage.put(Key(f'{user_id}_last_name'), user_data.last_name)

        user, _ = await Client.objects.aget_or_create(
            vk_id=user_id,
            defaults={
                'first_name': await cls.storage.get(Key(f'{user_id}_first_name')),
                'last_name': await cls.storage.get(Key(f'{user_id}_last_name')),
                'vk_profile': f'https://vk.com/id{user_id}'
            }
        )
        await cls.storage.put(Key(f'{user_id}_instance'), user)

        if event.text.lower().strip() in ['start', '/start', 'начать', 'старт']:
            user_state = 'START'
        else:
            user_state = user.bot_state

        state_handler = cls.states_functions[user_state]
        user.bot_state = await state_handler(event, cls.storage)
        await sync_to_async(user.save)()
