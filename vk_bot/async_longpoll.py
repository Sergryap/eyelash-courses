import asyncio
import random
import json
import aiohttp
import logging
import re

from django.conf import settings
from textwrap import dedent
from time import sleep
from asgiref.sync import sync_to_async
from more_itertools import chunked
from courses.models import Client, Course, Office
from django.utils import timezone
from aiohttp import client_exceptions
from .buttons import (
    get_start_buttons,
    get_menu_button,
    get_course_buttons,
    check_phone_button,
    get_course_menu_buttons
)

logger = logging.getLogger('telegram')


async def get_long_poll_server(session: aiohttp.ClientSession, token: str, group_id: int, /):
    get_album_photos_url = 'https://api.vk.com/method/groups.getLongPollServer'
    params = {'access_token': token, 'v': '5.131', 'group_id': group_id}
    async with session.get(get_album_photos_url, params=params) as res:
        res.raise_for_status()
        response = json.loads(await res.text())
        key = response['response']['key']
        server = response['response']['server']
        ts = response['response']['ts']
        return key, server, ts


async def send_message(
        connect,
        user_id: int,
        message: str,
        user_ids: str = None,
        keyboard: str = None,
        attachment: str = None,
        payload: str = None,
        sticker_id: int = None,
        lat: str = None,
        long: str = None,
):
    send_message_url = 'https://api.vk.com/method/messages.send'
    params = {
        'access_token': connect['token'], 'v': '5.131',
        'user_id': user_id,
        'user_ids': user_ids,
        'random_id': random.randint(0, 1000),
        'message': message,
        'attachment': attachment,
        'keyboard': keyboard,
        'payload': payload,
        'sticker_id': sticker_id,
        'lat': lat,
        'long': long
    }
    for param, value in params.copy().items():
        if value is None:
            del params[param]
    async with connect['session'].post(send_message_url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())


async def get_user(connect, user_ids: str):
    get_users_url = 'https://api.vk.com/method/users.get'
    params = {
        'access_token': connect['token'], 'v': '5.131',
        'user_ids': user_ids
    }
    async with connect['session'].get(get_users_url, params=params) as res:
        res.raise_for_status()
        response = json.loads(await res.text())
        return response.get('response')


async def event_handler(connect, event):
    """Главный обработчик событий"""

    user_id = event['object']['message']['from_id']
    start_buttons = ['start', '/start', 'начать', 'старт', '+']
    text = event['object']['message']['text'].lower().strip()
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    if not connect['redis_db'].get(f'{user_id}_first_name'):
        user_data = await get_user(connect, user_id)
        if user_data:
            connect['redis_db'].set(f'{user_id}_first_name', user_data[0].get('first_name'))
            connect['redis_db'].set(f'{user_id}_last_name', user_data[0].get('last_name'))
    user, _ = await Client.objects.async_get_or_create(
        vk_id=user_id,
        defaults={
            'first_name': connect['redis_db'].get(f'{user_id}_first_name').decode('utf-8'),
            'last_name': connect['redis_db'].get(f'{user_id}_last_name').decode('utf-8'),
            'vk_profile': f'https://vk.com/id{user_id}',
        }
    )
    if text in start_buttons or payload.get('button') == 'start':
        user_state = 'START'
    else:
        user_state = user.bot_state

    states_functions = {
        'START': start,
        'MAIN_MENU': main_menu_handler,
        'COURSE': handle_course_info,
        'PHONE': enter_phone,
    }
    state_handler = states_functions[user_state]
    user.bot_state = await state_handler(connect, event)
    exist_phone = connect['redis_db'].get(f'{user_id}_phone')
    user.phone_number = exist_phone.decode('utf-8') if exist_phone else user.phone_number
    await sync_to_async(user.save)()


async def start(connect, event):
    user_id = event['object']['message']['from_id']
    first_name = connect['redis_db'].get(f'{user_id}_first_name').decode('utf-8')
    text = event['object']['message']['text'].lower().strip()
    start_buttons = ['start', '/start', 'начать', 'старт', '+']
    msg = 'MENU:'
    if text in start_buttons:
        msg = f'''
            Привет, {first_name}, я бот этого чата.
            Здесь ты можешь узнать всю актуальную информацию о наших курсах и при желании оставить заявку.
            Чтобы начать нажми "MENU"             
            '''
        buttons = [
            [
                {
                    'action': {'type': 'text', 'payload': {'button': 'start'}, 'label': '☰ MENU'},
                    'color': 'positive'
                }
            ],
            [
                {
                    'action': {'type': 'text', 'payload': {'button': 'future_courses'}, 'label': 'Предстоящие курсы'},
                    'color': 'positive'
                }
            ],
        ]
        keyboard = json.dumps({'inline': True, 'buttons': buttons}, ensure_ascii=False)
        await send_message(
            connect,
            user_id=user_id,
            message=dedent(msg),
            keyboard=keyboard,
        )
        return 'MAIN_MENU'

    await send_message(
        connect,
        user_id=user_id,
        message=dedent(msg),
        keyboard=await get_start_buttons()
    )
    return 'MAIN_MENU'


async def main_menu_handler(connect, event):
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    if payload:
        return await send_main_menu_answer(connect, event)
    else:
        return await answer_arbitrary_text(connect, event)


async def handle_course_info(connect, event):
    user_id = event['object']['message']['from_id']
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    if payload and payload.get('course_pk'):
        course_pk = payload['course_pk']
        course = await Course.objects.async_get(pk=course_pk)
        course_date = await sync_to_async(course.scheduled_at.strftime)("%d.%m.%Y")
        course_images = await sync_to_async(course.images.all)()
        attachment = None

        if await sync_to_async(bool)(course_images):
            if course.name == 'Фотогалерея':
                attachment_sequence = [image.image_vk_id for image in course_images if image.image_vk_id]
                random.shuffle(attachment_sequence)
            else:
                random_images = random.choices(course_images, k=4)
                attachment_sequence = [image.image_vk_id for image in random_images if image.image_vk_id]
            if attachment_sequence:
                attachment = ','.join(attachment_sequence)

        if course.name == 'Фотогалерея':
            await send_message(
                connect,
                user_id=user_id,
                message='Фото с прошедших курсов:',
                attachment=attachment,
                keyboard=await get_course_menu_buttons(
                    back=payload['button'], course=course, user_id=user_id
                )
            )
            return 'MAIN_MENU'

        text = f'''            
            {course.name.upper()}:

            Дата: {course_date}
            Программа: {await sync_to_async(lambda: course.program)()}
            Лектор: {await sync_to_async(lambda: course.lecture)()}            
            Продолжительность: {course.duration} д.

            О ПРОГРАММЕ КУРСА:
            {await sync_to_async(lambda: course.program.short_description)()}

            РАСПИСАНИЕ КУРСА:
            {await sync_to_async(lambda: course.short_description)()}
            '''

        await send_message(
            connect,
            user_id=user_id,
            message=dedent(text),
            attachment=attachment,
            keyboard=await get_course_menu_buttons(
                back=payload['button'], course=course, user_id=user_id
            )
        )

    elif payload:
        return await send_main_menu_answer(connect, event)
    else:
        return await answer_arbitrary_text(connect, event)

    return 'MAIN_MENU'


async def enter_phone(connect, event):
    user_id = event['object']['message']['from_id']
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    user_instance = await Client.objects.async_get(vk_id=user_id)
    course_pk = connect['redis_db'].get(f'{user_id}_current_course')
    course = await Course.objects.async_get(pk=course_pk)
    user_info = {
        'first_name': connect['redis_db'].get(f'{user_id}_first_name').decode('utf-8'),
        'last_name': connect['redis_db'].get(f'{user_id}_last_name').decode('utf-8')
    }
    # если номер существует
    if payload and payload.get('check_phone'):
        if payload['check_phone'] == 'true':
            await entry_user_to_course(connect, user_id, user_info, user_instance, course)
            connect['redis_db'].delete(f'{user_id}_current_course')
            return 'MAIN_MENU'
        # если клиент захотел указать другой номер
        else:
            text = f'''
                 {user_info['first_name']}, чтобы записаться на курс,
                 отправьте актуальный номер телефона в ответном сообщении:                   
                 '''
            await send_message(
                connect,
                user_id=user_id,
                message=dedent(text)
            )
            return 'PHONE'
    # проверка формата введенного номера
    elif payload and payload.get('button') == 'admin_msg':
        user_msg = f'{user_info["first_name"]}, введите и отправьте ваше сообщение:'
        await send_message(
            connect,
            user_id=user_id,
            message=user_msg
        )
        return 'MAIN_MENU'
    else:
        phone = event['object']['message']['text']
        pattern = re.compile(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$')
        if pattern.findall(phone):
            connect['redis_db'].delete(f'{user_id}_current_course')
            norm_phone = ''.join(['+7'] + [i for i in phone if i.isdigit()][-10:])
            connect['redis_db'].set(f'{user_id}_phone', norm_phone)
            await entry_user_to_course(connect, user_id, user_info, user_instance, course)
            return 'MAIN_MENU'
        else:
            text = '''
            Вы ввели неверный номер телефона.
            Попробуйте еще раз.
            Либо вернитесь в меню
            '''
            await send_message(
                connect,
                user_id=user_id,
                message=dedent(text),
                keyboard=await get_menu_button(color='secondary', inline=True)
            )
            return 'PHONE'

#######################################
# Функции, не являющиеся хэндлерами
#######################################


async def send_main_menu_answer(connect, event):
    user_id = event['object']['message']['from_id']
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    user_instance = await Client.objects.async_get(vk_id=user_id)
    user_info = {
        'first_name': connect['redis_db'].get(f'{user_id}_first_name').decode('utf-8'),
        'last_name': connect['redis_db'].get(f'{user_id}_last_name').decode('utf-8')
    }
    # отправка курсов пользователя
    if payload.get('button') == 'client_courses':
        client_courses = await sync_to_async(user_instance.courses.filter)(published_in_bot=True)
        return await send_courses(
            connect, event, client_courses,
            'Вы еше не записаны ни на один курс:',
            'Курсы, на которые вы записаны или проходили:',
            'Еще ваши курсы',
            back='client_courses',
        )
    # отправка предстоящих курсов
    elif payload.get('button') == 'future_courses':
        future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now(), published_in_bot=True)
        return await send_courses(
            connect, event, future_courses,
            'Пока нет запланированных курсов:',
            'Предстоящие курсы. Выберите для детальной информации',
            'Еще предстоящие курсы:',
            back='future_courses',
        )
    # отправка прошедших курсов
    elif payload.get('button') == 'past_courses':
        past_courses = await Course.objects.async_filter(scheduled_at__lte=timezone.now(), published_in_bot=True)
        return await send_courses(
            connect, event, past_courses,
            'Еше нет прошедших курсов:',
            'Прошедшие курсы',
            'Еще прошедшие курсы:',
            back='past_courses',
        )
    elif payload.get('button') == 'admin_msg':
        user_msg = f'{user_info["first_name"]}, введите и отправьте ваше сообщение:'
        await send_message(connect, user_id, message=user_msg)
    # отправка геолокации
    elif payload.get('button') == 'search_us':
        office = await Office.objects.async_first()
        text = f'{user_info["first_name"]}, мы находимся по адресу:\n\n{office.address}\n{office.description}'
        await send_message(
            connect,
            user_id=user_id,
            message=text,
            lat=str(office.lat),
            long=str(office.long),
            attachment=settings.OFFICE_PHOTO,
            keyboard=await get_menu_button(color='primary', inline=True)
        )
    # запись/отмена участия на курсе
    elif payload.get('entry'):
        course_pk = payload.get('entry')
        course = await Course.objects.async_get(pk=course_pk)
        if payload.get('cancel'):
            text = f'''
                 {user_info['first_name']}, вы отменили запись на курс: {course.name}.
                 Спасибо, что проявили интерес к нашей школе.
                 Вы всегда можете вернуться снова и выбрать подходящий курс.
                 '''
            await send_message(
                connect,
                user_id=user_id,
                message=dedent(text),
                keyboard=await get_menu_button(color='secondary', inline=True)
            )
            await sync_to_async(course.clients.remove)(user_instance)
            await sync_to_async(course.save)()
            logger.warning(f'Клиент https://vk.com/id{user_id} отменил запись на курс **{course.name.upper()}**')
        else:
            connect['redis_db'].set(f'{user_id}_current_course', course_pk)
            if user_instance.phone_number:
                text = f'''
                    Чтобы записаться проверьте ваш номер телефона:
                    {user_instance.phone_number}                        
                    '''
                await send_message(
                    connect,
                    user_id=user_id,
                    message=dedent(text),
                    keyboard=await check_phone_button()
                )
            else:
                text = f'''
                     {user_info['first_name']}, чтобы записаться на курс, укажите ваш номер телефона.                         
                     '''
                await send_message(
                    connect,
                    user_id=user_id,
                    message=dedent(text),
                    keyboard=await get_menu_button(color='secondary', inline=True))
            return 'PHONE'

    return 'MAIN_MENU'


async def answer_arbitrary_text(connect, event):
    user_id = event['object']['message']['from_id']
    user_instance = await Client.objects.async_get(vk_id=user_id)
    vk_profile = user_instance.vk_profile
    admin_msg = f'''
            Сообщение от {vk_profile}
            в чате https://vk.com/gim{settings.VK_GROUP_ID}:
            "{event['object']['message']['text']}"
            '''
    user_msg = f'''
        Ваше сообщение отправлено.
        Мы обязательно свяжемся с Вами!
        Можете отправить еще, либо вернуться в меню.
        '''
    await send_message(
        connect,
        user_id=settings.ADMIN_IDS,
        user_ids=settings.ADMIN_IDS,
        message=dedent(admin_msg)
    )
    await asyncio.sleep(0.2)
    await send_message(
        connect,
        user_id=user_id,
        message=dedent(user_msg),
        keyboard=await get_menu_button(color='secondary', inline=True)
    )
    return 'MAIN_MENU'


async def send_courses(connect, event, courses, msg1, msg2, msg3, /, *, back):
    user_id = event['object']['message']['from_id']
    i = 0
    for client_courses_part in await sync_to_async(chunked)(courses, 5):
        i += 1
        msg = msg2 if i == 1 else msg3
        keyboard = await get_course_buttons(client_courses_part, back=back)
        await send_message(
            connect,
            user_id=user_id,
            message=msg,
            keyboard=keyboard
        )
    if i == 0:
        await send_message(
            connect,
            user_id=user_id,
            message=msg1,
            keyboard=await get_menu_button(color='secondary', inline=True)
        )
    return 'COURSE'


async def entry_user_to_course(connect, user_id, user_info, user_instance, course):
    name = user_info['first_name']
    text = f'''
         {name}, вы записаны на курс:
         **{course.name.upper()}**
         Спасибо, что выбрали нашу школу.
         В ближайшее время мы свяжемся с вами для подтверждения вашего участия.
         '''
    await send_message(
        connect,
        user_id=user_id,
        message=dedent(text),
        keyboard=await get_menu_button(color='secondary', inline=True)
    )
    await sync_to_async(course.clients.add)(user_instance)
    await sync_to_async(course.save)()
    client_vk = f'https://vk.com/id{user_id}'
    redis_phone = connect['redis_db'].get(f'{user_id}_phone')
    phone = redis_phone.decode('utf-8') if redis_phone else user_instance.phone_number
    logger.warning(f'Клиент {name}\n{client_vk}:\nТел: {phone}\nзаписался на курс **{course.name.upper()}**')


async def listen_server():
    token = settings.VK_TOKEN
    async with aiohttp.ClientSession() as session:
        key, server, ts = await get_long_poll_server(session, token, settings.VK_GROUP_ID)
        connect = {'session': session, 'token': token, 'redis_db': settings.REDIS_DB}
        while True:
            try:
                params = {'act': 'a_check', 'key': key, 'ts': ts, 'wait': 25}
                async with session.get(server, params=params) as res:
                    res.raise_for_status()
                    response = json.loads(await res.text())
                if 'failed' in response:
                    if response['failed'] == 1:
                        ts = response['ts']
                    elif response['failed'] == 2:
                        key, __, __ = await get_long_poll_server(session, token, settings.VK_GROUP_ID)
                    elif response['failed'] == 3:
                        key, __, ts = await get_long_poll_server(session, token, settings.VK_GROUP_ID)
                    continue
                ts = response['ts']
                for event in response['updates']:
                    if event['type'] != 'message_new':
                        continue
                    await asyncio.sleep(0.2)
                    await event_handler(connect, event)
            except ConnectionError as err:
                sleep(5)
                logger.warning(f'Соединение было прервано: {err}', stack_info=True)
                key, server, ts = await get_long_poll_server(session, token, settings.VK_GROUP_ID)
                continue
            except client_exceptions.ServerTimeoutError as err:
                logger.warning(f'Ошибка ReadTimeout: {err}', stack_info=True)
                key, server, ts = await get_long_poll_server(session, token, settings.VK_GROUP_ID)
                continue
            except Exception as err:
                logger.exception(err)
                key, server, ts = await get_long_poll_server(session, token, settings.VK_GROUP_ID)
        logger.critical('Бот вышел из цикла и упал:', stack_info=True)
