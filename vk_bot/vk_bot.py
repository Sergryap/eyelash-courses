from asgiref.sync import sync_to_async
from vkwave.bots import SimpleBotEvent
from vkwave.bots.storage.types import Key
from vkwave.bots.storage.storages import Storage
from courses.models import Client, Course
from vkwave.bots.utils.keyboards.keyboard import Keyboard, ButtonColor
from django.utils import timezone


async def handle_users_reply(event: SimpleBotEvent):
    """Главный хэндлер для всех сообщений"""

    storage = Storage()
    user_id = event.user_id
    api = event.api_ctx

    states_functions = {
        'START': start,
        'STEP_1': handle_step_1


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


async def start(event: SimpleBotEvent, storage: Storage):
    user_id = event.user_id
    user_instance = await storage.get(Key(f'{user_id}_instance'))
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    msg = f'{user_info["first_name"]}, выберите, чтобы вы хотели:'
    keyboard = Keyboard(one_time=False, inline=True)
    buttons = [
        ('Ваши курсы', 'client_courses'),
        ('Предстоящие курсы', 'future_courses'),
        ('Прошедшие курсы', 'past_courses'),
        ('Написать администратору', 'admin_msg'),
        ('Как нас найти', 'search_us')
    ]
    for i, (btn, payload) in await sync_to_async(enumerate)(buttons, start=1):
        keyboard.add_text_button(
            btn,
            ButtonColor.PRIMARY,
            payload={'button': payload}
        )
        if i != len(buttons):
            keyboard.add_row()
    await event.answer(message=msg, keyboard=keyboard.get_keyboard())

    return 'STEP_1'


async def handle_step_1(event: SimpleBotEvent, storage: Storage):
    user_id = event.user_id
    user_instance = await storage.get(Key(f'{user_id}_instance'))
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    keyboard = Keyboard(one_time=False, inline=True)
    if event.payload and event.payload['button'] == 'client_courses':
        client_courses = user_instance.courses.all()
        count_courses = await client_courses.acount()
        if client_courses:
            msg = 'Курсы, на которые вы записаны или проходили:'
            for i, course in await sync_to_async(enumerate)(client_courses, start=1):
                keyboard.add_text_button(
                    course.name,
                    ButtonColor.PRIMARY,
                    payload={'button': course.pk}
                )
                if i != count_courses:
                    keyboard.add_row()
            keyboard = keyboard.get_keyboard()
        else:
            keyboard = None
            msg = 'Вы еше не записаны ни на один курс:'

        await event.answer(message=msg, keyboard=keyboard)
    elif event.payload and event.payload['button'] == 'future_courses':
        future_courses = Course.objects.filter(scheduled_at__gt=timezone.now())
        count_courses = await future_courses.acount()
        if future_courses:
            msg = 'Предстоящие курсы. Выберите для детальной информации'
            for i, course in await sync_to_async(enumerate)(future_courses, start=1):
                keyboard.add_text_button(
                    course.name,
                    ButtonColor.PRIMARY,
                    payload={'button': course.pk}
                )
                if i != count_courses:
                    keyboard.add_row()
        else:
            keyboard = None
            msg = 'Пока нет запланированных курсов:'
        await event.answer(message=msg, keyboard=keyboard.get_keyboard())
    elif event.payload and event.payload['button'] == 'past_courses':
        past_courses = Course.objects.filter(scheduled_at__lte=timezone.now())
        count_courses = await past_courses.acount()
        msg = 'Прошедшие курсы. Выберите для детальной информации'
        for i, course in await sync_to_async(enumerate)(past_courses, start=1):
            keyboard.add_text_button(
                course.name,
                ButtonColor.PRIMARY,
                payload={'button': course.pk}
            )
            if i != count_courses:
                keyboard.add_row()
        await event.answer(message=msg, keyboard=keyboard.get_keyboard())
    elif event.payload and event.payload['button'] == 'admin_msg':
        msg = f'{user_info["first_name"]}, введите и отправьте ваше сообщение:'
    elif event.payload and event.payload['button'] == 'search_us':
        pass

    return 'STEP_1'
