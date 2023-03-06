from asgiref.sync import sync_to_async
from vkwave.bots import SimpleBotEvent, SimpleLongPollBot
from vkwave.bots.storage.types import Key
from courses.models import Client


class VkBot:

    def __init__(self, token, group_id, client_router, states_functions, storage):

        self.token = token
        self.group_id = group_id
        self.updater = SimpleLongPollBot(tokens=token, group_id=group_id)
        self.updater.dispatcher.add_router(client_router)
        self.states_functions = states_functions
        self.storage = storage

    async def handle_users_reply(self, event: SimpleBotEvent):
        user_id = event.user_id
        api = event.api_ctx

        if not await self.storage.contains(Key(f'{user_id}_first_name')):
            user_data = (await api.users.get(user_ids=user_id)).response[0]
            await self.storage.put(Key(f'{user_id}_first_name'), user_data.first_name)
            await self.storage.put(Key(f'{user_id}_last_name'), user_data.last_name)

        user, _ = await Client.objects.aget_or_create(
            vk_id=user_id,
            defaults={
                'first_name': await self.storage.get(Key(f'{user_id}_first_name')),
                'last_name': await self.storage.get(Key(f'{user_id}_last_name')),
                'vk_profile': f'https://vk.com/id{user_id}'
            }
        )
        await self.storage.put(Key(f'{user_id}_instance'), user)

        if event.text.lower().strip() in ['start', '/start', 'начать', 'старт']:
            user_state = 'START'
        else:
            user_state = user.bot_state

        state_handler = self.states_functions[user_state]
        user.bot_state = await state_handler(event, self.storage)
        await sync_to_async(user.save)()
