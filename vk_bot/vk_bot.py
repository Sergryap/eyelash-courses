from asgiref.sync import sync_to_async
from vkwave.bots import SimpleBotEvent
from vkwave.bots.storage.types import Key
from vkwave.bots.storage.storages import Storage
from courses.models import Client
from . import handlers


async def handle_users_reply(event: SimpleBotEvent):
    storage = Storage()
    user_id = event.user_id
    api = event.api_ctx

    states_functions = {
        'START': handlers.start,


    }

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
    if not await storage.contains(Key(f'{user_id}_instance')):
        await storage.put(Key(f'{user_id}_instance'), user)

    if event.text.lower().strip() in ['start', '/start', 'начать', 'старт']:
        user_state = 'START'
    else:
        user_state = user.bot_state

    state_handler = states_functions[user_state]
    user.bot_state = await state_handler(event, storage)
    await sync_to_async(user.save)()
