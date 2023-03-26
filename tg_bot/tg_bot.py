import asyncio
import json
import aiohttp
import logging
import random
import re

from courses.models import Client, Course, Office
from django.utils import timezone
from aiohttp import client_exceptions
from time import sleep
from asgiref.sync import sync_to_async
from more_itertools import chunked
from .keyboard import get_callback_keyboard, get_course_buttons, get_course_menu_buttons, check_phone_button
from textwrap import dedent
from django.conf import settings

from .tg_api import send_message, send_location, send_photo


logger = logging.getLogger('telegram')


async def send_main_menu_answer(connect, event):
    event_info = await get_event_info(event)
    chat_id = event_info['chat_id']
    user_reply = event_info['user_reply']
    first_name = event_info['first_name']
    user_instance = await Client.objects.async_get(telegram_id=chat_id)
    # отправка курсов пользователя
    if user_reply == 'client_courses':
        client_courses = await sync_to_async(user_instance.courses.filter)(published_in_bot=True)
        return await send_courses(
            connect, event, client_courses,
            'Вы еше не записаны ни на один курс:',
            'Курсы, на которые вы записаны или проходили:',
            'Еще ваши курсы',
            back='client_courses',
        )
    # отправка предстоящих курсов
    elif user_reply == 'future_courses':
        future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now(), published_in_bot=True)
        return await send_courses(
            connect, event, future_courses,
            'Пока нет запланированных курсов:',
            'Предстоящие курсы. Выберите для детальной информации',
            'Еще предстоящие курсы:',
            back='future_courses',
        )
    # отправка прошедших курсов
    elif user_reply == 'past_courses':
        past_courses = await Course.objects.async_filter(scheduled_at__lte=timezone.now(), published_in_bot=True)
        return await send_courses(
            connect, event, past_courses,
            'Еше нет прошедших курсов:',
            'Прошедшие курсы',
            'Еще прошедшие курсы:',
            back='past_courses',
        )
    elif user_reply == 'admin_msg':
        await send_message(
            connect,
            chat_id=chat_id,
            msg=f'{first_name}, введите и отправьте ваше сообщение:'
        )
    # отправка геолокации
    elif user_reply == 'search_us':
        office = await Office.objects.async_first()
        text = f'{first_name}, мы находимся по адресу:\n\n{office.address}\n{office.description}'
        await send_photo(
            connect,
            chat_id=chat_id,
            photo=f'https://vk.com/{settings.OFFICE_PHOTO}',
            caption=text
        )
        await send_location(
            connect,
            chat_id=chat_id,
            lat=str(office.lat),
            long=str(office.long),
        )
    # запись/отмена участия на курсе
    elif user_reply.split('_')[0] == 'en':
        course_pk = int(user_reply.split('_')[1])
        course = await Course.objects.async_get(pk=course_pk)
        if user_reply.split('_')[2] == 'c':
            text = f'''
                 {first_name}, вы отменили запись на курс: {course.name}.
                 Спасибо, что проявили интерес к нашей школе.
                 Вы всегда можете вернуться снова и выбрать подходящий курс.
                 '''
            await send_message(
                connect,
                chat_id=chat_id,
                msg=dedent(text),
            )
            await sync_to_async(course.clients.remove)(user_instance)
            await sync_to_async(course.save)()
            logger.warning(f'Клиент {first_name}_tg_ID{chat_id} отменил запись на курс **{course.name.upper()}**')
        else:
            connect['redis_db'].set(f'tg_{chat_id}_current_course', course_pk)
            if user_instance.phone_number:
                text = f'''
                    Чтобы записаться проверьте ваш номер телефона:
                    {user_instance.phone_number}                        
                    '''
                await send_message(
                    connect,
                    chat_id=chat_id,
                    msg=dedent(text),
                    reply_markup=await check_phone_button()
                )
            else:
                text = f'''
                     {first_name}, чтобы записаться на курс, укажите ваш номер телефона.                         
                     '''
                await send_message(
                    connect,
                    chat_id=chat_id,
                    msg=dedent(text))
            return 'PHONE'
    elif event.get('callback_query') and user_reply.split(':')[0] == 'c':
        return await handle_course_info(connect, event)
    return 'MAIN_MENU'


async def answer_arbitrary_text(connect, event):
    event_info = await get_event_info(event)
    chat_id = event_info['chat_id']
    user_reply = event_info['user_reply']
    first_name = event_info['first_name']
    user_instance = await Client.objects.async_get(telegram_id=chat_id)
    vk_profile = user_instance.vk_profile
    admin_msg = f'''
            Сообщение от t.me/{event['message']['chat']['username']}:
            "{user_reply}"
            '''
    user_msg = f'''
        Ваше сообщение отправлено.
        Мы обязательно свяжемся с Вами!
        Можете отправить еще, либо вернуться в меню.
        '''
    logger.warning(admin_msg)
    await send_message(
        connect,
        chat_id=chat_id,
        msg=dedent(user_msg),
        reply_markup=await get_callback_keyboard([('☰ MENU', 'start')], 1, inline=False)
    )
    return 'MAIN_MENU'


async def entry_user_to_course(connect, chat_id, first_name, user_instance, course):
    text = f'''
         {first_name}, вы записаны на курс:
         **{course.name.upper()}**
         Спасибо, что выбрали нашу школу.
         В ближайшее время мы свяжемся с вами для подтверждения вашего участия.
         '''
    await send_message(
        connect,
        chat_id=chat_id,
        msg=dedent(text),
        reply_markup=await get_callback_keyboard([('☰ MENU', 'start')], 1, inline=False)
    )
    await sync_to_async(course.clients.add)(user_instance)
    await sync_to_async(course.save)()
    redis_phone = connect['redis_db'].get(f'tg_{chat_id}_phone')
    phone = redis_phone.decode('utf-8') if redis_phone else user_instance.phone_number
    logger.warning(f'Клиент {first_name}\ntg_{chat_id}:\nТел: {phone}\nзаписался на курс **{course.name.upper()}**')


async def send_courses(connect, event, courses, msg1, msg2, msg3, /, *, back):
    event_info = await get_event_info(event)
    chat_id = event_info['chat_id']
    i = 0
    for client_courses_part in await sync_to_async(chunked)(courses, 5):
        i += 1
        msg = msg2 if i == 1 else msg3
        keyboard = await get_course_buttons(client_courses_part, back=back)
        await send_message(
            connect,
            chat_id=chat_id,
            msg=msg,
            reply_markup=keyboard
        )
    if i == 0:
        buttons = [
            ('☰ MENU', 'start'),
        ]
        await send_message(
            connect,
            chat_id=chat_id,
            msg=msg1,
            reply_markup=await get_callback_keyboard(buttons, 2, inline=False)
        )
    return 'COURSE'


async def get_event_info(event):
    if event.get('message'):
        user_reply = event['message']['text']
        chat_id = event['message']['chat']['id']
        first_name = event['message']['chat']['first_name']
        last_name = event['message']['chat'].get('last_name')
    elif event.get('callback_query'):
        user_reply = event['callback_query']['data']
        chat_id = event['callback_query']['message']['chat']['id']
        first_name = event['callback_query']['message']['chat']['first_name']
        last_name = event['callback_query']['message']['chat'].get('last_name')
    else:
        return
    return {
        'user_reply': user_reply,
        'chat_id': chat_id,
        'first_name': first_name,
        'last_name': last_name
    }


async def start(connect, event):
    event_info = await get_event_info(event)
    start_buttons = ['/start', '+']
    msg = 'MENU:'
    if event_info['user_reply'] in start_buttons:
        msg = f'''
            Привет, {event_info['first_name']}, я бот этого чата.
            Здесь ты можешь узнать всю актуальную информацию о наших курсах и при желании оставить заявку.
            Чтобы начать нажми "MENU"             
            '''
        buttons = [('☰ MENU', 'start')]
        await send_message(
            connect,
            chat_id=event_info['chat_id'],
            msg=dedent(msg),
            reply_markup=await get_callback_keyboard(buttons, 2, inline=False)
        )
        return 'MAIN_MENU'
    buttons = [
        ('Предстоящие курсы', 'future_courses'),
        ('Прошедшие курсы', 'past_courses'),
        ('Ваши курсы', 'client_courses'),
        ('Как нас найти', 'search_us'),
        ('Написать администратору', 'admin_msg'),
    ]
    await send_message(
        connect,
        chat_id=event_info['chat_id'],
        msg=msg,
        reply_markup=await get_callback_keyboard(buttons, 2)
    )
    return 'MAIN_MENU'


async def main_menu_handler(connect, event):
    if event.get('callback_query'):
        return await send_main_menu_answer(connect, event)
    elif event.get('message'):
        return await answer_arbitrary_text(connect, event)
    return 'START'


async def handle_course_info(connect, event):
    """ Отправка сообщения о конкретном курсе """
    event_info = await get_event_info(event)
    chat_id = event_info['chat_id']
    user_reply = event_info['user_reply']

    if event.get('callback_query') and user_reply.split(':')[0] == 'c':
        course_pk = int(user_reply.split(':')[1])
        back = user_reply.split(':')[2]
        course = await Course.objects.async_get(pk=course_pk)
        course_date = await sync_to_async(course.scheduled_at.strftime)("%d.%m.%Y")
        course_images = await sync_to_async(course.images.all)()
        attachment_sequence = []
        if await sync_to_async(bool)(course_images):
            if course.name == 'Фотогалерея':
                attachment_sequence = [image.image_vk_id for image in course_images if image.image_vk_id]
                random.shuffle(attachment_sequence)
            else:
                random_images = random.choices(course_images, k=4)
                attachment_sequence = [image.image_vk_id for image in random_images if image.image_vk_id]

        if course.name == 'Фотогалерея':
            await send_message(
                connect,
                chat_id=chat_id,
                msg='Фото с прошедших курсов:',
            )
            for photo in attachment_sequence:
                await send_photo(
                    connect,
                    chat_id=chat_id,
                    photo=f'https://vk.com/{photo}'
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

            СОДЕРЖАНИЕ КУРСА:
            {await sync_to_async(lambda: course.short_description)()}
            '''

        await send_photo(
            connect,
            chat_id=chat_id,
            photo=f'https://vk.com/{random.choice(attachment_sequence)}'
        )
        await send_message(
            connect,
            chat_id=chat_id,
            msg=dedent(text),
            reply_markup=await get_course_menu_buttons(back, course_pk, chat_id)
        )

    elif event.get('callback_query'):
        return await send_main_menu_answer(connect, event)
    else:
        return await answer_arbitrary_text(connect, event)

    return 'MAIN_MENU'


async def enter_phone(connect, event):
    event_info = await get_event_info(event)
    chat_id = event_info['chat_id']
    user_reply = event_info['user_reply']
    first_name = event_info['first_name']
    user_instance = await Client.objects.async_get(telegram_id=chat_id)
    course_pk = connect['redis_db'].get(f'tg_{chat_id}_current_course')
    course = await Course.objects.async_get(pk=course_pk)

    # если номер существует
    if event.get('callback_query') and user_reply.split('_')[0] == 'phone':
        if user_reply.split('_')[1] == 'true':
            await entry_user_to_course(connect, chat_id, first_name, user_instance, course)
            connect['redis_db'].delete(f'tg_{chat_id}_current_course')
            return 'MAIN_MENU'
        # если клиент захотел указать другой номер
        else:
            text = f'''
                 {first_name}, чтобы записаться на курс,
                 отправьте актуальный номер телефона в ответном сообщении:                   
                 '''
            await send_message(
                connect,
                chat_id=chat_id,
                msg=dedent(text)
            )
            return 'PHONE'
    # проверка формата введенного номера
    elif event.get('callback_query') and user_reply == 'admin_msg':
        user_msg = f'{first_name}, введите и отправьте ваше сообщение:'
        await send_message(
            connect,
            chat_id=chat_id,
            msg=user_msg
        )
        return 'MAIN_MENU'
    else:
        phone = event['message']['text']
        pattern = re.compile(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$')
        if pattern.findall(phone):
            connect['redis_db'].delete(f'tg_{chat_id}_current_course')
            norm_phone = ''.join(['+7'] + [i for i in phone if i.isdigit()][-10:])
            connect['redis_db'].set(f'tg_{chat_id}_phone', norm_phone)
            await entry_user_to_course(connect, chat_id, first_name, user_instance, course)
            return 'MAIN_MENU'
        else:
            text = '''
            Вы ввели неверный номер телефона.
            Попробуйте еще раз.
            Либо вернитесь в меню
            '''
            await send_message(
                connect,
                chat_id=chat_id,
                msg=dedent(text),
                reply_markup=await get_callback_keyboard([('☰ MENU', 'start')], 1, inline=False)
            )
            return 'PHONE'


async def handle_event(connect, event):
    """Главный обработчик событий"""
    event_info = await get_event_info(event)
    start_buttons = ['start', '/start', 'начать', 'старт', '+', '☰ menu', '/menu']
    user, _ = await Client.objects.async_get_or_create(
        telegram_id=event_info['chat_id'],
        defaults={
            'first_name': event_info['first_name'],
            'last_name': event_info['last_name'],
        }
    )
    if event_info['user_reply'].lower() in start_buttons:
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
    exist_phone = connect['redis_db'].get(f'tg_{event_info["chat_id"]}_phone')
    user.phone_number = exist_phone.decode('utf-8') if exist_phone else user.phone_number
    await sync_to_async(user.save)()


async def listen_server():
    """Получение событий сервера"""

    tg_token = settings.TG_TOKEN
    url = f'https://api.telegram.org/bot{tg_token}/getUpdates'
    params = {'timeout': 5, 'limit': 1}
    async with aiohttp.ClientSession() as session:
        connect = {'session': session, 'token': tg_token, 'redis_db': settings.REDIS_DB}
        while True:
            try:
                await asyncio.sleep(0.1)
                async with session.get(url, params=params) as res:
                    res.raise_for_status()
                    updates = json.loads(await res.text())
                if not updates.get('result') or not updates['ok']:
                    continue
                event = updates['result'][-1]
                params['offset'] = event['update_id'] + 1
                await handle_event(connect, event)
            except ConnectionError:
                sleep(5)
                logger.warning(f'Соединение было прервано', stack_info=True)
                continue
            except client_exceptions.ServerTimeoutError:
                logger.warning(f'Ошибка ReadTimeout', stack_info=True)
                continue
            except Exception as err:
                logger.exception(err)
                print(err)
