from vkwave.bots import SimpleBotEvent
from vkwave.bots.storage.types import Key
from vkwave.bots.storage.storages import Storage


async def start(event: SimpleBotEvent, storage: Storage):
    user_id = event.user_id
    msg = event.text.strip()
    user_instance = await storage.get(Key(f'{user_id}_instance'))
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    await event.answer(message=msg)

    return 'START'
