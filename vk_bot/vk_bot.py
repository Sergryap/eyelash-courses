import asyncio
import random
import aiohttp
import json
import re

from django.conf import settings
from asgiref.sync import sync_to_async
from vkwave.bots import SimpleBotEvent
from vkwave.bots.storage.types import Key
from vkwave.bots.storage.storages import Storage
from courses.models import Client, Course, Program, CourseClient
from vkwave.bots.utils.keyboards.keyboard import Keyboard, ButtonColor
from django.utils import timezone
from more_itertools import chunked
from .vk_lib import (
    BUTTONS_START,
    get_course_msg,
    get_button_menu,
    get_button_course_menu,
    entry_user_to_course,
    check_phone_button,
    save_image_vk_id
)
from textwrap import dedent

storage = Storage()


async def handle_users_reply(event: SimpleBotEvent):
    """Главный хэндлер для всех сообщений"""

    user_id = event.user_id
    api = event.api_ctx
    states_functions = {
        'START': start,
        'MAIN_MENU': main_menu_handler,
        'COURSE': handle_course_info,
        'PHONE': enter_phone,
    }

    if not await storage.contains(Key(f'{user_id}_first_name')):
        user_data = (await api.users.get(user_ids=user_id)).response[0]
        await storage.put(Key(f'{user_id}_first_name'), user_data.first_name)
        await storage.put(Key(f'{user_id}_last_name'), user_data.last_name)

    user, _ = await Client.objects.async_get_or_create(
        vk_id=user_id,
        defaults={
            'first_name': await storage.get(Key(f'{user_id}_first_name')),
            'last_name': await storage.get(Key(f'{user_id}_last_name')),
            'vk_profile': f'https://vk.com/id{user_id}',
        }
    )

    if (event.text.lower().strip() in ['start', '/start', 'начать', 'старт']
            or event.payload and event.payload.get('button') == 'start'):
        user_state = 'START'
        await event.answer(message='Переход в главное меню', keyboard=await get_button_menu(inline=False))
    else:
        user_state = user.bot_state

    state_handler = states_functions[user_state]
    user.bot_state = await state_handler(event)
    user.phone_number = await storage.get(Key(f'{user_id}_phone'), user.phone_number)
    await sync_to_async(user.save)()


async def start(event: SimpleBotEvent):
    user_id = event.user_id
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

    return 'MAIN_MENU'


async def main_menu_handler(event: SimpleBotEvent):
    user_id = event.user_id
    api = event.api_ctx
    user_instance = await Client.objects.async_get(vk_id=user_id)
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    if event.payload:
        # отправка курсов пользователя
        if event.payload.get('button') == 'client_courses':
            client_courses = await sync_to_async(user_instance.courses.all)()
            i = 0
            for client_courses_part in await sync_to_async(chunked)(client_courses, 5):
                i += 1
                if i == 1:
                    successful_msg = 'Курсы, на которые вы записаны или проходили:'
                else:
                    successful_msg = 'Еще ваши курсы'
                keyboard = await get_course_msg(client_courses_part, back='client_courses')
                await event.answer(message=successful_msg, keyboard=keyboard)
            if i == 0:
                keyboard = Keyboard(one_time=False, inline=True)
                keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})
                await event.answer(message='Вы еше не записаны ни на один курс:', keyboard=keyboard.get_keyboard())
            return 'COURSE'

        # отправка предстоящих курсов
        elif event.payload.get('button') == 'future_courses':
            future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now(), published_in_bot=True)
            if not future_courses:
                keyboard = Keyboard(one_time=False, inline=True)
                keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})
                await event.answer(message='Пока нет запланированных курсов:', keyboard=keyboard.get_keyboard())
                return 'COURSE'
            for i, future_courses_part in await sync_to_async(enumerate)(chunked(future_courses, 5), start=1):
                if i == 1:
                    successful_msg = 'Предстоящие курсы. Выберите для детальной информации'
                else:
                    successful_msg = 'Еще предстоящие курсы:'
                keyboard = await get_course_msg(future_courses_part, back='future_courses')
                await event.answer(message=successful_msg, keyboard=keyboard)
            return 'COURSE'

        # отправка прошедших курсов
        elif event.payload.get('button') == 'past_courses':
            past_courses = await Course.objects.async_filter(scheduled_at__lte=timezone.now(), published_in_bot=True)
            if not past_courses:
                keyboard = Keyboard(one_time=False, inline=True)
                keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})
                await event.answer(message='Еше нет прошедших курсов:', keyboard=keyboard.get_keyboard())
                return 'COURSE'
            for i, past_courses_part in await sync_to_async(enumerate)(chunked(past_courses, 5), start=1):
                if i == 1:
                    successful_msg = 'Прошедшие курсы. Выберите для детальной информации'
                else:
                    successful_msg = 'Еще прошедшие курсы:'
                keyboard = await get_course_msg(past_courses_part, back='past_courses')
                await event.answer(message=successful_msg, keyboard=keyboard)
            return 'COURSE'

        elif event.payload.get('button') == 'admin_msg':
            user_msg = f'{user_info["first_name"]}, введите и отправьте ваше сообщение:'
            await event.answer(message=user_msg)
        # отправка геолокации
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
                lat=settings.OFFICE_LAT,
                long=settings.OFFICE_LONG
            )
            await event.answer(
                message='В главное меню:',
                keyboard=await get_button_menu()
            )
        # запись/отмена участия на курсе
        elif event.payload.get('entry'):
            course_pk = event.payload.get('entry')
            course = await Course.objects.async_get(pk=course_pk)
            if event.payload.get('cancel'):
                text = f'''
                     {user_info['first_name']}, вы отменили запись на курс: {course.name}.
                     Спасибо, что проявили интерес к нашей школе.
                     Вы всегда можете вернуться снова и выбрать подходящий курс.
                     '''
                await event.answer(
                    message=dedent(text),
                    keyboard=await get_button_menu()
                )
                await sync_to_async(course.clients.remove)(user_instance)
                await sync_to_async(course.save)()
            else:
                await storage.put(Key(f'{user_id}_current_course'), course)
                if user_instance.phone_number:
                    text = f'''
                        Чтобы записаться проверьте ваш номер телефона:
                        {user_instance.phone_number}                        
                        '''
                    await event.answer(
                        message=dedent(text),
                        keyboard=await check_phone_button()
                    )
                else:
                    text = f'''
                         {user_info['first_name']}, чтобы записаться на курс, укажите ваш номер телефона.                         
                         '''
                    await event.answer(
                        message=dedent(text),
                        keyboard=await get_button_menu()
                    )
                return 'PHONE'
    # обработка произвольного сообщения пользователя
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

    return 'MAIN_MENU'


async def handle_course_info(event: SimpleBotEvent):
    api = event.api_ctx
    user_id = event.user_id
    user_instance = await Client.objects.async_get(vk_id=user_id)
    if event.payload and event.payload.get('course_pk'):
        course_pk = event.payload['course_pk']
        course = await Course.objects.async_get(pk=course_pk)
        course_date = await sync_to_async(course.scheduled_at.strftime)("%d.%m.%Y")
        course_images = await sync_to_async(course.images.all)()
        attachment = None

        if await sync_to_async(bool)(course_images):
            random_image = await sync_to_async(random.choice)(course_images)
            if not random_image.image_vk_id:
                await save_image_vk_id(random_image)
            else:
                attachment = random_image.image_vk_id

        text = f'''            
            {course.name.upper()}:
            
            Дата: {course_date}
            Программа: {await sync_to_async(lambda: course.program)()}
            Лектор: {await sync_to_async(lambda: course.lecture)()}            
            Продолжительность: {course.duration} д.
            '''
        program_text = f'''
            О ПРОГРАММЕ КУРСА:
            {await sync_to_async(lambda: course.program.short_description)()}
            '''
        description_text = f'''
            СОДЕРЖАНИЕ КУРСА:
            {await sync_to_async(lambda: course.short_description)()}
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
                keyboard=await get_button_course_menu(
                    back=event.payload['button'], course_pk=course_pk, user_id=user_id
                )
            )
        else:
            await event.answer(
                message=dedent(program_text),
                keyboard=await get_button_course_menu(
                    back=event.payload['button'], course_pk=course_pk, user_id=user_id
                )
            )

    return 'MAIN_MENU'


async def enter_phone(event: SimpleBotEvent):
    user_id = event.user_id
    user_instance = await Client.objects.async_get(vk_id=user_id)
    course = await storage.get(Key(f'{user_id}_current_course'))
    user_info = {
        'first_name': await storage.get(Key(f'{user_id}_first_name')),
        'last_name': await storage.get(Key(f'{user_id}_last_name'))
    }
    # если номер существует
    if event.payload and event.payload.get('check_phone'):
        if event.payload['check_phone'] == 'true':
            await entry_user_to_course(event, user_info, user_instance, course)
            await storage.delete(Key(f'{user_id}_current_course'))
            return 'MAIN_MENU'
        # если клиент захотел указать другой номер
        else:
            text = f'''
                 {user_info['first_name']}, чтобы записаться на курс, укажите актуальный номер телефона.                         
                 '''
            await event.answer(
                message=dedent(text),
                keyboard=await get_button_menu()
            )
            return 'PHONE'
    # проверка формата введенного номера
    else:
        phone = event.text
        pattern = re.compile(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$')
        if pattern.findall(phone):
            await storage.delete(Key(f'{user_id}_current_course'))
            norm_phone = ''.join(['+7'] + [i for i in phone if i.isdigit()][-10:])
            await storage.put(Key(f'{user_id}_phone'), norm_phone)
            await entry_user_to_course(event, user_info, user_instance, course)
            return 'MAIN_MENU'
        else:
            text = '''
            Вы ввели неверный номер телефона.
            Попробуйте еще раз.
            Либо вернитесь в меню
            '''
            await event.answer(
                message=dedent(text),
                keyboard=await get_button_menu()
            )
            return 'PHONE'
