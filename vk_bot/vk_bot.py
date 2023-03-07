import random
import aiohttp
import json

from django.conf import settings
from asgiref.sync import sync_to_async
from vkwave.bots import SimpleBotEvent
from vkwave.bots.storage.types import Key
from vkwave.bots.storage.storages import Storage
from courses.models import Client, Course, Program
from vkwave.bots.utils.keyboards.keyboard import Keyboard, ButtonColor
from django.utils import timezone
from .vk_lib import BUTTONS_START, get_course_msg, get_button_menu
from textwrap import dedent


async def handle_users_reply(event: SimpleBotEvent):
    """Главный хэндлер для всех сообщений"""

    storage = Storage()
    user_id = event.user_id
    api = event.api_ctx

    states_functions = {
        'START': start,
        'STEP_1': handle_step_1,
        'COURSE': handle_course_info


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

    if (event.text.lower().strip() in ['start', '/start', 'начать', 'старт']
            or event.payload and event.payload.get('button') == 'start'):
        user_state = 'START'
        await event.answer(message='Переход в главное меню', keyboard=await get_button_menu(inline=False))
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
    buttons = BUTTONS_START
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
    api = event.api_ctx
    user_instance = await storage.get(Key(f'{user_id}_instance'))
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    if event.payload:
        if event.payload.get('button') == 'client_courses':
            client_courses = await sync_to_async(user_instance.courses.all)()
            msg, keyboard = await get_course_msg(
                client_courses,
                successful_msg='Курсы, на которые вы записаны или проходили:',
                not_successful_msg='Вы еше не записаны ни на один курс:'
            )
            await event.answer(message=msg, keyboard=keyboard)

            return 'COURSE'

        elif event.payload.get('button') == 'future_courses':
            future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now())
            msg, keyboard = await get_course_msg(
                future_courses,
                successful_msg='Предстоящие курсы. Выберите для детальной информации',
                not_successful_msg='Пока нет запланированных курсов:'
            )
            await event.answer(message=msg, keyboard=keyboard)

            return 'COURSE'

        elif event.payload.get('button') == 'past_courses':
            past_courses = await Course.objects.async_filter(scheduled_at__lte=timezone.now())
            msg, keyboard = await get_course_msg(
                past_courses,
                successful_msg='Прошедшие курсы. Выберите для детальной информации',
                not_successful_msg='Еше нет прошедших курсов:'
            )
            await event.answer(message=msg, keyboard=keyboard)

            return 'COURSE'

        elif event.payload.get('button') == 'admin_msg':
            user_msg = f'{user_info["first_name"]}, введите и отправьте ваше сообщение:'
            await event.answer(message=user_msg)
        elif event.payload.get('button') == 'search_us':
            text = f'''
                 {user_info['first_name']}, мы находимся по адресу:
                 📍 г.Пермь, ул. Тургенева, д. 23.
                 
                 Это малоэтажное кирпичное здание слева от ТЦ "Агат" 
                 Вход через "Идеал-Лик", большой стеклянный тамбур.
                 '''
            await api.messages.send(
                user_id=user_id,
                random_id=random.randint(0, 1000),
                message=dedent(text),
                lat=58.017794,
                long=56.293045
            )
            await event.answer(
                message='В главное меню:',
                keyboard=await get_button_menu()
            )
    elif event.text:
        msg = event.text
        vk_profile = user_instance.vk_profile
        admin_msg = f'''
        Сообщение от {vk_profile} в чате https://vk.com/gim{settings.VK_GROUP_ID}:
        "{msg}"
        '''
        user_msg = f'''
        Ваше сообщение отправлено. Мы обязательно свяжемся с Вами!
        '''
        await api.messages.send(
            random_id=random.randint(0, 1000),
            user_ids=settings.ADMIN_IDS,
            message=admin_msg
        )
        await event.answer(
            message=user_msg,
            keyboard=await get_button_menu()
        )

    return 'STEP_1'


async def handle_course_info(event: SimpleBotEvent, storage: Storage):
    api = event.api_ctx
    user_id = event.user_id
    if event.payload:
        course_pk = event.payload['course_pk']
        course = await Course.objects.async_get(pk=course_pk)
        course_date = await sync_to_async(course.scheduled_at.strftime)("%d.%m.%Y")
        course_images = await sync_to_async(course.images.all)()
        attachment = None

        if await sync_to_async(bool)(course_images):
            random_image = await sync_to_async(random.choice)(course_images)
            upload = await api.photos.get_messages_upload_server(peer_id=0)
            image_link = random_image.image.path if settings.DEBUG else random_image.image.url

            with open(image_link, 'rb') as file:
                async with aiohttp.ClientSession() as session:
                    async with session.post(upload.response.upload_url, data={'photo': file}) as res:
                        response = await res.text()
            upload_photo = await sync_to_async(json.loads)(response)

            photo = await api.photos.save_messages_photo(
                photo=upload_photo['photo'],
                server=upload_photo['server'],
                hash=upload_photo['hash']
            )
            if photo.response:
                attachment = f'photo{photo.response[0].owner_id}_{photo.response[0].id}'

        text = f'''            
            {course.name.upper()}:
            
            Дата: {course_date}
            Программа: {await sync_to_async(lambda: course.program)()}
            Лектор: {await sync_to_async(lambda: course.lecture)()}            
            Продолжительность: {course.duration} д.
            '''
        program_text = f'''
            О ПРОГРАММЕ КУРСА:
            {await sync_to_async(lambda: course.program.description)()}
            '''
        description_text = f'''
            СОДЕРЖАНИЕ КУРСА:
            {await sync_to_async(lambda: course.description)()}
            '''

        await event.answer(
            message=dedent(text),
            attachment=attachment
        )
        if description_text:
            await event.answer(
                message=dedent(program_text)
            )
            await event.answer(
                message=dedent(description_text),
                keyboard=await get_button_menu(),
            )
        else:
            await event.answer(
                message=dedent(program_text),
                keyboard=await get_button_menu(),
            )

    return 'STEP_1'

