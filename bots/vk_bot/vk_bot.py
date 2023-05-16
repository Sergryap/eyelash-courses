import asyncio
import random
import json
import logging
import re

from .vk_api import VkApi
from django.conf import settings
from textwrap import dedent
from asgiref.sync import sync_to_async
from more_itertools import chunked
from courses.models import Client, Course, Office
from django.utils import timezone
from .buttons import (
    get_start_buttons,
    get_menu_button,
    get_course_buttons,
    check_phone_button,
    get_course_menu_buttons
)

logger = logging.getLogger('telegram')


async def handle_event(api: VkApi, event: dict):
    """Главный обработчик событий"""

    if api.sending_tasks:  # Записываем отложенные задачи в глобальное пространство
        for name_task, task in api.sending_tasks.items():
            globals()[name_task] = task
        api.vk_sending_tasks = False

    user_id = event['object']['message']['from_id']
    start_buttons = ['start', '/start', 'начать', 'старт', '+']
    text = event['object']['message']['text'].lower().strip()
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    if not api.redis_db.get(f'{user_id}_first_name'):
        user_data = await api.get_user(user_id)
        if user_data:
            api.redis_db.set(f'{user_id}_first_name', user_data[0].get('first_name'))
            api.redis_db.set(f'{user_id}_last_name', user_data[0].get('last_name'))
    user, _ = await Client.objects.async_get_or_create(
        vk_id=user_id,
        defaults={
            'first_name': api.redis_db.get(f'{user_id}_first_name').decode('utf-8'),
            'last_name': api.redis_db.get(f'{user_id}_last_name').decode('utf-8'),
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
    user.bot_state = await state_handler(api, event)
    exist_phone = api.redis_db.get(f'{user_id}_phone')
    user.phone_number = exist_phone.decode('utf-8') if exist_phone else user.phone_number
    await sync_to_async(user.save)()


async def start(api: VkApi, event: dict):
    user_id = event['object']['message']['from_id']
    first_name = api.redis_db.get(f'{user_id}_first_name').decode('utf-8')
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
        await api.send_message(
            user_id=user_id,
            message=dedent(msg),
            keyboard=keyboard,
        )
        return 'MAIN_MENU'

    await api.send_message(
        user_id=user_id,
        message=dedent(msg),
        keyboard=await get_start_buttons()
    )
    return 'MAIN_MENU'


async def main_menu_handler(api: VkApi, event: dict):
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    if payload:
        return await send_main_menu_answer(api, event)
    else:
        return await answer_arbitrary_text(api, event)


async def handle_course_info(api: VkApi, event: dict):
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
            await api.send_message(
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

        await api.send_message(
            user_id=user_id,
            message=dedent(text),
            attachment=attachment,
            keyboard=await get_course_menu_buttons(
                back=payload['button'], course=course, user_id=user_id
            )
        )

    elif payload:
        return await send_main_menu_answer(api, event)
    else:
        return await answer_arbitrary_text(api, event)

    return 'MAIN_MENU'


async def enter_phone(api: VkApi, event: dict):
    user_id = event['object']['message']['from_id']
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    user_instance = await Client.objects.async_get(vk_id=user_id)
    course_pk = api.redis_db.get(f'{user_id}_current_course')
    course = await Course.objects.async_get(pk=course_pk)
    user_info = {
        'first_name': api.redis_db.get(f'{user_id}_first_name').decode('utf-8'),
        'last_name': api.redis_db.get(f'{user_id}_last_name').decode('utf-8')
    }
    # если номер существует
    if payload and payload.get('check_phone'):
        if payload['check_phone'] == 'true':
            await entry_user_to_course(api, user_id, user_info, user_instance, course)
            api.redis_db.delete(f'{user_id}_current_course')
            return 'MAIN_MENU'
        # если клиент захотел указать другой номер
        else:
            text = f'''
                 {user_info['first_name']}, чтобы записаться на курс,
                 отправьте актуальный номер телефона в ответном сообщении:                   
                 '''
            await api.send_message(
                user_id=user_id,
                message=dedent(text)
            )
            return 'PHONE'
    # проверка формата введенного номера
    elif payload and payload.get('button') == 'admin_msg':
        user_msg = f'{user_info["first_name"]}, введите и отправьте ваше сообщение:'
        await api.send_message(
            user_id=user_id,
            message=user_msg
        )
        return 'MAIN_MENU'
    else:
        phone = event['object']['message']['text']
        pattern = re.compile(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$')
        if pattern.findall(phone):
            api.redis_db.delete(f'{user_id}_current_course')
            norm_phone = ''.join(['+7'] + [i for i in phone if i.isdigit()][-10:])
            api.redis_db.set(f'{user_id}_phone', norm_phone)
            await entry_user_to_course(api, user_id, user_info, user_instance, course)
            return 'MAIN_MENU'
        else:
            text = '''
            Вы ввели неверный номер телефона.
            Попробуйте еще раз.
            Либо вернитесь в меню
            '''
            await api.send_message(
                user_id=user_id,
                message=dedent(text),
                keyboard=await get_menu_button(color='secondary', inline=True)
            )
            return 'PHONE'

#######################################
# Функции, не являющиеся хэндлерами
#######################################


async def send_main_menu_answer(api: VkApi, event: dict):
    user_id = event['object']['message']['from_id']
    payload = json.loads(event['object']['message'].get('payload', '{}'))
    user_instance = await Client.objects.async_get(vk_id=user_id)
    user_info = {
        'first_name': api.redis_db.get(f'{user_id}_first_name').decode('utf-8'),
        'last_name': api.redis_db.get(f'{user_id}_last_name').decode('utf-8')
    }
    # отправка курсов пользователя
    if payload.get('button') == 'client_courses':
        client_courses = await sync_to_async(user_instance.courses.filter)(published_in_bot=True)
        return await send_courses(
            api, event, client_courses,
            'Вы еше не записаны ни на один курс:',
            'Курсы, на которые вы записаны или проходили:',
            'Еще ваши курсы',
            back='client_courses',
        )
    # отправка предстоящих курсов
    elif payload.get('button') == 'future_courses':
        future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now(), published_in_bot=True)
        return await send_courses(
            api, event, future_courses,
            'Пока нет запланированных курсов:',
            'Предстоящие курсы. Выберите для детальной информации',
            'Еще предстоящие курсы:',
            back='future_courses',
        )
    # отправка прошедших курсов
    elif payload.get('button') == 'past_courses':
        past_courses = await Course.objects.async_filter(scheduled_at__lte=timezone.now(), published_in_bot=True)
        return await send_courses(
            api, event, past_courses,
            'Еше нет прошедших курсов:',
            'Прошедшие курсы',
            'Еще прошедшие курсы:',
            back='past_courses',
        )
    elif payload.get('button') == 'admin_msg':
        user_msg = f'{user_info["first_name"]}, введите и отправьте ваше сообщение:'
        await api.send_message(user_id, message=user_msg)
    # отправка геолокации
    elif payload.get('button') == 'search_us':
        office = await Office.objects.async_first()
        text = f'{user_info["first_name"]}, мы находимся по адресу:\n\n{office.address}\n{office.description}'
        await api.send_message(
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
            await api.send_message(
                user_id=user_id,
                message=dedent(text),
                keyboard=await get_menu_button(color='secondary', inline=True)
            )
            canceled_task = globals().get(f'remind_record_vk_{user_id}_{course.pk}')
            if canceled_task:
                canceled_task.cancel()
            await sync_to_async(course.clients.remove)(user_instance)
            await sync_to_async(course.save)()
            logger.warning(f'Клиент https://vk.com/id{user_id} отменил запись на курс **{course.name.upper()}**')
        else:
            api.redis_db.set(f'{user_id}_current_course', course_pk)
            if user_instance.phone_number:
                text = f'''
                    Чтобы записаться проверьте ваш номер телефона:
                    {user_instance.phone_number}                        
                    '''
                await api.send_message(
                    user_id=user_id,
                    message=dedent(text),
                    keyboard=await check_phone_button()
                )
            else:
                text = f'''
                     {user_info['first_name']}, чтобы записаться на курс, укажите ваш номер телефона.                         
                     '''
                await api.send_message(
                    user_id=user_id,
                    message=dedent(text),
                    keyboard=await get_menu_button(color='secondary', inline=True))
            return 'PHONE'

    return 'MAIN_MENU'


async def answer_arbitrary_text(api: VkApi, event: dict):
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
    await api.send_message(
        user_id=settings.ADMIN_IDS,
        user_ids=settings.ADMIN_IDS,
        message=dedent(admin_msg)
    )
    await asyncio.sleep(0.2)
    await api.send_message(
        user_id=user_id,
        message=dedent(user_msg),
        keyboard=await get_menu_button(color='secondary', inline=True)
    )
    return 'MAIN_MENU'


async def send_courses(api: VkApi, event: dict, courses, msg1, msg2, msg3, /, *, back):
    user_id = event['object']['message']['from_id']
    i = 0
    for client_courses_part in await sync_to_async(chunked)(courses, 5):
        i += 1
        msg = msg2 if i == 1 else msg3
        keyboard = await get_course_buttons(client_courses_part, back=back)
        await api.send_message(
            user_id=user_id,
            message=msg,
            keyboard=keyboard
        )
    if i == 0:
        await api.send_message(
            user_id=user_id,
            message=msg1,
            keyboard=await get_menu_button(color='secondary', inline=True)
        )
    return 'COURSE'


async def entry_user_to_course(api: VkApi, user_id, user_info, user_instance, course):
    name = user_info['first_name']
    text = f'''
        {name}, вы записаны на курс:
        **{course.name.upper()}**
        Спасибо, что выбрали нашу школу.
        В ближайшее время мы свяжемся с вами для подтверждения вашего участия.
        '''
    office = await Office.objects.async_first()
    reminder_text = await api.create_reminder_text(name, course, office)
    await api.send_message(
        user_id=user_id,
        message=dedent(text),
        keyboard=await get_menu_button(color='secondary', inline=True)
    )
    remind_before = 86400 - 6 * 3600
    time_offset = 5 * 3600
    time_to_start = (course.scheduled_at - timezone.now()).total_seconds()
    interval = time_to_start - time_offset - remind_before
    if interval > 0:
        globals()[f'remind_record_vk_{user_id}_{course.pk}'] = (
            await api.send_message_later(
                user_id,
                dedent(reminder_text),
                interval=interval,
                keyboard=await get_menu_button(color='secondary', inline=True)
            )
        )
    await sync_to_async(course.clients.add)(user_instance)
    await sync_to_async(course.save)()
    client_vk = f'https://vk.com/id{user_id}'
    redis_phone = api.redis_db.get(f'{user_id}_phone')
    phone = redis_phone.decode('utf-8') if redis_phone else user_instance.phone_number
    logger.warning(f'Клиент {name}\n{client_vk}:\nТел: {phone}\nзаписался на курс **{course.name.upper()}**')
