from .vk_bot import Key, SimpleBotEvent
from vkwave.bots.storage.storages import Storage

storage = Storage()


async def start(event: SimpleBotEvent):
    user_id = event.user_id
    msg = event.text.strip()
    user_instance = await storage.get(Key(f'{user_id}_instance'))
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    await event.answer(message=msg)

    return 'START'
