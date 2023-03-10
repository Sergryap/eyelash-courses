import aiohttp
import json

from django.conf import settings
from asgiref.sync import sync_to_async
from vkwave.bots import SimpleBotEvent
from vkwave.bots.utils.keyboards.keyboard import Keyboard, ButtonColor
from textwrap import dedent
from courses.models import Course, CourseClient
from vkwave.api import API, Token
from vkwave.api.token.token import UserSyncSingleToken

BUTTONS_START = [
    ('Предстоящие курсы', 'future_courses'),
    ('Ваши курсы', 'client_courses'),
    ('Прошедшие курсы', 'past_courses'),
    ('Написать администратору', 'admin_msg'),
    ('Как нас найти', 'search_us')
]


async def get_course_msg(course_instances, back, successful_msg, not_successful_msg):
    count_courses = await course_instances.acount()
    keyboard = Keyboard(one_time=False, inline=True)
    if count_courses:
        msg = successful_msg
        for i, course in await sync_to_async(enumerate)(course_instances, start=1):
            keyboard.add_text_button(
                course.name,
                ButtonColor.PRIMARY,
                payload={'course_pk': course.pk, 'button': back}
            )
            keyboard.add_row()
        keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})
    else:
        msg = not_successful_msg
        keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})
    keyboard = keyboard.get_keyboard()

    return msg, keyboard


async def get_button_menu(inline=True):
    keyboard = Keyboard(one_time=False, inline=inline)
    buttons_color = ButtonColor.SECONDARY
    keyboard.add_text_button('☰ MENU', buttons_color, payload={'button': 'start'})

    return keyboard.get_keyboard()


async def get_button_course_menu(back, course_pk, user_id):
    keyboard = Keyboard(one_time=False, inline=True)
    course_clients = await CourseClient.objects.async_filter(course=course_pk)
    course_client_ids = [await sync_to_async(lambda: user.client.vk_id)() for user in course_clients]
    if back != 'client_courses' and back != 'past_courses' and user_id not in course_client_ids:
        keyboard.add_text_button('ЗАПИСАТЬСЯ НА КУРС', ButtonColor.PRIMARY, payload={'entry': course_pk})
        keyboard.add_row()
    elif user_id in course_client_ids:
        keyboard.add_text_button('ОТМЕНИТЬ ЗАПИСЬ', ButtonColor.PRIMARY, payload={'entry': course_pk, 'cancel': 1})
        keyboard.add_row()
    keyboard.add_text_button('НАЗАД', ButtonColor.PRIMARY, payload={'button': back})
    keyboard.add_row()
    keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})

    return keyboard.get_keyboard()


async def entry_user_to_course(event: SimpleBotEvent, user_info, user_instance, course):
    text = f'''
         {user_info['first_name']}, вы записаны на курс:
         **{course.name.upper()}**
         Спасибо, что выбрали нашу школу.
         В ближайшее время мы свяжемся с вами для подтверждения вашего участия.
         '''
    await event.answer(
        message=dedent(text),
        keyboard=await get_button_menu()
    )
    await sync_to_async(course.clients.add)(user_instance)
    await sync_to_async(course.save)()


async def check_phone_button():
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add_text_button('НОМЕР ВЕРНЫЙ', ButtonColor.PRIMARY, payload={'check_phone': 'true'})
    keyboard.add_row()
    keyboard.add_text_button('УКАЖУ ДРУГОЙ', ButtonColor.PRIMARY, payload={'check_phone': 'false'})
    keyboard.add_row()
    keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})

    return keyboard.get_keyboard()


async def save_image_vk_id(obj):
    if not obj.image_vk_id:
        image_link = obj.image.path if settings.DEBUG else obj.image.url
        token = Token(settings.VK_TOKEN)
        session = API(tokens=UserSyncSingleToken(token))
        api = session.get_context()
        upload = await api.photos.get_messages_upload_server(peer_id=0)
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
            obj.image_vk_id = attachment
            await sync_to_async(obj.save)()
