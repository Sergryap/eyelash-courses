import json
import logging
import random
import re
import os

from courses.models import Client, Course, Office
from django.utils import timezone
from asgiref.sync import sync_to_async
from more_itertools import chunked
from .keyboard import get_callback_keyboard, get_course_buttons, get_course_menu_buttons, check_phone_button
from textwrap import dedent
from django.conf import settings
from .tg_api import TgApi
from .tg_types import Update, Message, CallbackQuery

logger = logging.getLogger('telegram')


async def send_main_menu_answer(api: TgApi, event: Update):
    message, user_reply = await get_message_user_replay(event)
    user_instance = await Client.objects.async_get(telegram_id=message.chat.id)
    # отправка курсов пользователя
    if user_reply == 'client_courses':
        client_courses = await sync_to_async(user_instance.courses.filter)(published_in_bot=True)
        return await send_courses(
            api, event, client_courses,
            '_Вы еше не записаны ни на один курс_',
            '_Курсы, на которые вы записаны или проходили:_',
            '_Еще ваши курсы_',
            back='client_courses',
        )
    # отправка предстоящих курсов
    elif user_reply == 'future_courses':
        future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now(), published_in_bot=True)
        return await send_courses(
            api, event, future_courses,
            '_Пока нет запланированных курсов_',
            '*Предстоящие курсы.*\n_Выберите для детальной информации:_',
            '_Еще предстоящие курсы:_',
            back='future_courses',
        )
    # отправка прошедших курсов
    elif user_reply == 'past_courses':
        past_courses = await Course.objects.async_filter(scheduled_at__lte=timezone.now(), published_in_bot=True)
        return await send_courses(
            api, event, past_courses,
            '_Еше нет прошедших курсов_',
            '*Прошедшие курсы*',
            '_Еще прошедшие курсы:_',
            back='past_courses',
        )
    elif user_reply == 'admin_msg':
        await api.send_message(
            chat_id=message.chat.id,
            msg=f'_{message.chat.first_name}, введите и отправьте ваше сообщение:_',
            parse_mode='Markdown'
        )
    # отправка геолокации
    elif user_reply == 'search_us':
        office = await Office.objects.async_first()
        text = f'{message.chat.first_name}, мы находимся по адресу:\n<b>{office.address}</b>\n<i>{office.description}</i>'
        # await api.send_photo(
        #     chat_id=event.chat_id,
        #     photo=f'https://vk.com/{settings.OFFICE_PHOTO}',
        #     caption=text,
        #     parse_mode='HTML'
        # )
        reply_markup = json.dumps({'inline_keyboard': [[{'text': '☰ MENU', 'callback_data': 'start'}]]})
        await api.send_venue(
            chat_id=message.chat.id,
            lat=str(office.lat),
            long=str(office.long),
            title=office.title,
            address=office.address,
            reply_markup=reply_markup
        )
    # запись/отмена участия на курсе
    elif user_reply.split('_')[0] == 'en':
        course_pk = int(user_reply.split('_')[1])
        course = await Course.objects.async_get(pk=course_pk)
        if user_reply.split('_')[2] == 'c':
            text = f'''
                 {message.chat.first_name}, вы отменили запись на курс: *{course.name}*.
                 _Спасибо, что проявили интерес к нашей школе._
                 _Вы всегда можете вернуться снова и выбрать подходящий курс._
                 '''
            await api.send_message(
                chat_id=message.chat.id,
                msg=dedent(text),
                parse_mode='Markdown',
                reply_markup=json.dumps({'inline_keyboard': [[{'text': '☰ MENU', 'callback_data': 'start'}]]})
            )
            await api.delete_message_sending_tasks(course_pk, message.chat.id)
            await sync_to_async(course.clients.remove)(user_instance)
            await sync_to_async(course.save)()
            logger_msg = f'''
                Клиент t.me/{message.chat.username}
                Тел: {user_instance.phone_number}
                отменил запись на курс **{course.name.upper()}**'
                '''
            logger.warning(dedent(logger_msg))
        else:
            api.redis_db.set(f'tg_{message.chat.id}_current_course', course_pk)
            if user_instance.phone_number:
                text = f'''
                    _Чтобы записаться проверьте ваш номер телефона:_
                    *{user_instance.phone_number}*                        
                    '''
                await api.send_message(
                    chat_id=message.chat.id,
                    msg=dedent(text),
                    reply_markup=await check_phone_button(),
                    parse_mode='Markdown'
                )
            else:
                text = f'''
                     {message.chat.first_name}, чтобы записаться на курс, укажите ваш номер телефона.                         
                     '''
                await api.send_message(
                    chat_id=message.chat.id,
                    msg=dedent(text))
            return 'PHONE'
    elif event.callback_query and user_reply.split(':')[0] == 'c':
        return await handle_course_info(api, event)
    return 'MAIN_MENU'


async def answer_arbitrary_text(api: TgApi, event: Update):
    message, user_reply = await get_message_user_replay(event)
    admin_msg = f'''
        Сообщение от t.me/{message.chat.username}:
        "{user_reply}"
        '''
    user_msg = f'''
        _Ваше сообщение отправлено._
        _Мы обязательно свяжемся с Вами!_
        _Можете отправить еще, либо вернуться в меню._
        '''
    logger.warning(dedent(admin_msg))
    await api.send_message(
        chat_id=message.chat.id,
        msg=dedent(user_msg),
        reply_markup=await get_callback_keyboard([('☰ MENU', 'start')], 1, inline=False),
        parse_mode='Markdown'
    )
    return 'MAIN_MENU'


async def entry_user_to_course(api: TgApi, event: Update, user, course):
    message, _ = await get_message_user_replay(event)
    text = f'''
         {message.chat.first_name}, вы записаны на курс:
         *{course.name.upper()}*
         _Спасибо, что выбрали нашу школу._
         _В ближайшее время мы свяжемся с вами для подтверждения вашего участия._
         '''
    office = await Office.objects.async_first()
    reminder_text = await api.create_reminder_text(message.chat.first_name, course, office)
    await api.send_message(
        chat_id=message.chat.id,
        msg=dedent(text),
        reply_markup=json.dumps({'inline_keyboard': [[{'text': '☰ MENU', 'callback_data': 'start'}]]}),
        parse_mode='Markdown'
    )
    await api.create_message_sending_tasks(course.pk, message.chat.id, reminder_text=reminder_text)
    await sync_to_async(course.clients.add)(user)
    await sync_to_async(course.save)()
    redis_phone = api.redis_db.get(f'tg_{message.chat.id}_phone')
    phone = redis_phone.decode('utf-8') if redis_phone else user.phone_number
    logger_msg = f'''
        Клиент t.me/{message.chat.username}
        Тел: {phone}
        записался на курс **{course.name.upper()}**'
        '''
    logger.warning(dedent(logger_msg))


async def send_courses(api: TgApi, event: Update, courses, msg1, msg2, msg3, /, *, back):
    message, _ = await get_message_user_replay(event)
    i = 0
    for client_courses_part in await sync_to_async(chunked)(courses, 5):
        i += 1
        msg = msg2 if i == 1 else msg3
        keyboard = await get_course_buttons(client_courses_part, back=back)
        await api.send_message(
            chat_id=message.chat.id,
            msg=msg,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    if i == 0:
        buttons = [
            ('☰ MENU', 'start'),
        ]
        await api.send_message(
            chat_id=message.chat.id,
            msg=msg1,
            reply_markup=await get_callback_keyboard(buttons, 2, inline=False),
            parse_mode='Markdown'
        )
    return 'COURSE'


async def start(api: TgApi, event: Update):
    message, user_reply = await get_message_user_replay(event)
    start_buttons = ['/start']
    msg = 'MENU:'
    if user_reply in start_buttons:
        msg = f'''
            Привет, {message.chat.first_name}, я бот этого чата.
            Здесь ты можешь узнать всю актуальную информацию о наших курсах и при желании оставить заявку.
            Чтобы начать нажми *"MENU"*             
            '''
        buttons = [('☰ MENU', 'start')]
        await api.send_message(
            chat_id=message.chat.id,
            msg=dedent(msg),
            reply_markup=await get_callback_keyboard(buttons, 2, inline=False),
            parse_mode='Markdown'
        )
        return 'MAIN_MENU'
    elif user_reply == '/admin' and str(message.chat.id) in settings.TG_ADMIN_IDS:
        msg = f'''
            Для управления ботом нажми *ADMIN*             
            '''
        reply_markup = json.dumps(
            {'inline_keyboard': [[{
                'text': 'ADMIN',
                'url': settings.ADMIN_URL
            }]]}
        )
        await api.send_message(
            chat_id=message.chat.id,
            msg=msg,
            reply_markup=reply_markup,
            parse_mode='Markdown',
        )
        return 'MAIN_MENU'
    buttons = [
        ('Предстоящие курсы', 'future_courses'),
        ('Прошедшие курсы', 'past_courses'),
        ('Ваши курсы', 'client_courses'),
        ('Как нас найти', 'search_us'),
        ('Написать администратору', 'admin_msg'),
    ]
    await api.send_message(
        chat_id=message.chat.id,
        msg=msg,
        reply_markup=await get_callback_keyboard(buttons, 2, menu=False)
    )
    return 'MAIN_MENU'


async def main_menu_handler(api: TgApi, event: Update):
    if event.callback_query:
        return await send_main_menu_answer(api, event)
    elif event.message:
        return await answer_arbitrary_text(api, event)
    return 'START'


async def handle_course_info(api: TgApi, event: Update):
    """ Отправка сообщения о конкретном курсе """
    message, user_reply = await get_message_user_replay(event)
    if event.callback_query and event.callback_query.data.split(':')[0] == 'c':
        course_pk = int(user_reply.split(':')[1])
        back = user_reply.split(':')[2]
        course = await Course.objects.async_get(pk=course_pk)
        course_date = await sync_to_async(course.scheduled_at.strftime)("%d.%m.%Y")
        course_time = await sync_to_async(course.scheduled_at.strftime)("%H:%M")
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
            media = [{'type': 'photo', 'media': f'https://vk.com/{photo}'} for photo in attachment_sequence[:10]]
            await api.send_media_group(message.chat.id, media=media)
            await api.send_message(
                chat_id=message.chat.id,
                msg='*ФОТО С ПРОШЕДШИХ КУРСОВ*',
                parse_mode='Markdown',
                reply_markup=await get_course_menu_buttons(back, course, message.chat.id)
            )
            return 'MAIN_MENU'

        text_1 = f'''            
            <b>{course.name.upper()}:</b>

            Дата: <b><i>{course_date}</i></b>
            Время: <b><i>{course_time}</i></b>
            Программа: <b><i>{await sync_to_async(lambda: course.program)()}</i></b>
            Лектор: <b><i>{await sync_to_async(lambda: course.lecture)()}   </i></b>     
            Продолжительность: <b><i>{course.duration} д.</i></b>

            <b>О ПРОГРАММЕ КУРСА:</b>
            '''
        text_2 = await sync_to_async(lambda: course.program.short_description)()
        text = dedent(text_1) + '\n' + text_2
        await api.send_photo(
            chat_id=message.chat.id,
            photo=f'https://vk.com/{random.choice(attachment_sequence)}',
            caption=text,
            reply_markup=await get_course_menu_buttons(back, course, message.chat.id),
            parse_mode='HTML'
        )

    elif event.callback_query:
        return await send_main_menu_answer(api, event)
    else:
        return await answer_arbitrary_text(api, event)

    return 'MAIN_MENU'


async def enter_phone(api: TgApi, event: Update):
    message, user_reply = await get_message_user_replay(event)
    user_instance = await Client.objects.async_get(telegram_id=message.chat.id)
    course_pk = api.redis_db.get(f'tg_{message.chat.id}_current_course')
    course = await Course.objects.async_get(pk=course_pk)

    # если номер существует
    if event.callback_query and user_reply.split('_')[0] == 'phone':
        if user_reply.split('_')[1] == 'true':
            await entry_user_to_course(api, event, user_instance, course)
            api.redis_db.delete(f'tg_{message.chat.id}_current_course')
            return 'MAIN_MENU'
        # если клиент захотел указать другой номер
        else:
            text = f'''
                 {message.chat.first_name}, чтобы записаться на курс,
                 отправьте актуальный номер телефона в ответном сообщении:                   
                 '''
            await api.send_message(
                chat_id=message.chat.id,
                msg=f'_{dedent(text)}_',
                parse_mode='Markdown'
            )
            return 'PHONE'
    # проверка формата введенного номера
    elif event.callback_query and user_reply == 'admin_msg':
        await api.send_message(
            chat_id=message.chat.id,
            msg=f'_{message.chat.first_name}, введите и отправьте ваше сообщение:_',
            parse_mode='Markdown'
        )
        return 'MAIN_MENU'
    else:
        phone = user_reply
        pattern = re.compile(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$')
        if pattern.findall(phone):
            api.redis_db.delete(f'tg_{message.chat.id}_current_course')
            norm_phone = ''.join(['+7'] + [i for i in phone if i.isdigit()][-10:])
            api.redis_db.set(f'tg_{message.chat.id}_phone', norm_phone)
            await entry_user_to_course(api, event, user_instance, course)
            return 'MAIN_MENU'
        else:
            text = '''
            Вы ввели неверный номер телефона.
            Попробуйте еще раз.
            Либо вернитесь в меню
            '''
            await api.send_message(
                chat_id=message.chat.id,
                msg=f'_{dedent(text)}_',
                reply_markup=await get_callback_keyboard([('☰ MENU', 'start')], 1, inline=False),
                parse_mode='Markdown'
            )
            return 'PHONE'


async def handle_event(api: TgApi, event: Update):
    """Главный обработчик событий"""
    message, user_reply = await get_message_user_replay(event)
    if event.callback_query:
        await api.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    start_buttons = ['start', '/start', '/admin', 'начать', 'старт', '+', '☰ menu', '/menu']
    user, create = await Client.objects.async_get_or_create(
        telegram_id=message.chat.id,
        defaults={
            'first_name': message.chat.first_name,
            'last_name': message.chat.last_name,
            'registered_at': timezone.now() + timezone.timedelta(hours=api.hour_offset)
        }
    )
    if create:
        with open(os.path.join(os.getcwd(), 'bots', 'step_messages.json')) as file:
            msg_steps = json.load(file)
        task_name_start = f'tg_register_{message.chat.id}'
        await api.create_single_step_task(user, task_name_start, msg_steps['register'])
    if user_reply.lower() in start_buttons:
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
    user.bot_state = await state_handler(api, event)
    exist_phone = api.redis_db.get(f'tg_{message.chat.id}_phone')
    user.phone_number = exist_phone.decode('utf-8') if exist_phone else user.phone_number
    await sync_to_async(user.save)()


async def get_message_user_replay(event: Update):
    match event.message, event.callback_query:
        case Message(), None:
            message = event.message
            user_reply = event.message.text
        case None, CallbackQuery():
            message = event.callback_query.message
            user_reply = event.callback_query.data

    return message, user_reply
