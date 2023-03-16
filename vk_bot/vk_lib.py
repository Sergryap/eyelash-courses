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
from more_itertools import chunked
from typing import List

BUTTONS_START = [
    ('Предстоящие курсы', 'future_courses'),
    ('Ваши курсы', 'client_courses'),
    ('Прошедшие курсы', 'past_courses'),
    ('Написать администратору', 'admin_msg'),
    ('Как нас найти', 'search_us')
]


async def get_course_msg(course_instances, back):
    count_courses = len(course_instances)
    keyboard = Keyboard(one_time=False, inline=True)
    for course in course_instances:
        keyboard.add_text_button(
            course.name,
            ButtonColor.PRIMARY,
            payload={'course_pk': course.pk, 'button': back}
        )
        keyboard.add_row()
    keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})

    return keyboard.get_keyboard()


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


async def save_vkwave_image_vk_id(obj):
    """Загрузка фото на сервер ВК и получение image_vk_id для сообщения"""

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


async def save_image_vk_id(obj):
    """Загрузка фото на сервер ВК и получение image_vk_id для сообщения"""

    if not obj.image_vk_id:
        messages_upload_server_url = 'https://api.vk.com/method/photos.getMessagesUploadServer'
        save_messages_photo_url = 'https://api.vk.com/method/photos.saveMessagesPhoto'
        params = {'access_token': settings.VK_TOKEN, 'v': '5.131', 'peer_id': 0}
        image_link = obj.image.path if settings.DEBUG else obj.image.url

        async with aiohttp.ClientSession() as session:
            async with session.get(
                    messages_upload_server_url,
                    params={**params, 'peer_id': 0}
            ) as upload_res:
                upload_url = await sync_to_async(json.loads)(await upload_res.text())
            with open(image_link, 'rb') as file:
                async with session.post(upload_url['response']['upload_url'], data={'photo': file}) as res:
                    upload_photo = await sync_to_async(json.loads)(await res.text())
            async with session.post(save_messages_photo_url, params={
                **params,
                'photo': upload_photo['photo'],
                'server': upload_photo['server'],
                'hash': upload_photo['hash']
            }) as res:
                photo = await sync_to_async(json.loads)(await res.text())

        if photo.get('response'):
            attachment = f'photo{photo["response"][0]["owner_id"]}_{photo["response"][0]["id"]}'
            obj.image_vk_id = attachment
            await sync_to_async(obj.save)()


async def create_vk_album(obj):
    """Создание пустого альбома vk"""
    create_vk_album_url = 'https://api.vk.com/method/photos.createAlbum'
    params = {
        'access_token': settings.VK_USER_TOKEN,
        'v': '5.131',
        'title': obj.name,
        'group_id': settings.VK_GROUP_ID,
        'description': obj.short_description,
        'upload_by_admins_only': 1,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(create_vk_album_url, params=params) as response:
            return await sync_to_async(json.loads)(await response.text())


async def edit_vk_album(obj):
    """Редактирование существующего альбома VK"""

    edit_vk_album_url = 'https://api.vk.com/method/photos.editAlbum'
    params = {
        'access_token': settings.VK_USER_TOKEN,
        'v': '5.131',
        'album_id': str(obj.vk_album_id),
        'owner_id': '-' + str(settings.VK_GROUP_ID),
        'title': obj.name,
        'description': obj.short_description,
        'upload_by_admins_only': 1,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(edit_vk_album_url, params=params):
            pass


async def create_or_edit_vk_album(obj):
    """Создание пустого альбома vk либо редактирование существующего"""

    if not obj.vk_album_id:
        create_vk_album_url = 'https://api.vk.com/method/photos.createAlbum'
        params = {
            'access_token': settings.VK_USER_TOKEN,
            'v': '5.131',
            'title': obj.name,
            'group_id': settings.VK_GROUP_ID,
            'description': obj.short_description,
            'upload_by_admins_only': 1,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(create_vk_album_url, params=params) as response:
                album = await sync_to_async(json.loads)(await response.text())

        if album.get('response'):
            obj.vk_album_id = album['response']['id']
            await sync_to_async(obj.save)()
    else:
        edit_vk_album_url = 'https://api.vk.com/method/photos.editAlbum'
        params = {
            'access_token': settings.VK_USER_TOKEN,
            'v': '5.131',
            'album_id': str(obj.vk_album_id),
            'owner_id': '-' + str(settings.VK_GROUP_ID),
            'title': obj.name,
            'description': obj.short_description,
            'upload_by_admins_only': 1,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(edit_vk_album_url, params=params):
                pass


async def upload_photos_in_album(photo_instances, vk_album_id):
    """Загрузка фотографий в альбом группы ВК"""

    upload_server_url = 'https://api.vk.com/method/photos.getUploadServer'
    photos_save_url = 'https://api.vk.com/method/photos.save'
    params = {'access_token': settings.VK_USER_TOKEN, 'v': '5.131'}

    async with aiohttp.ClientSession() as session:
        for photo_sequence_part in chunked(photo_instances, 5):
            async with session.get(
                    upload_server_url,
                    params={**params, 'album_id': vk_album_id, 'group_id': settings.VK_GROUP_ID}
            ) as upload_res:
                upload = await sync_to_async(json.loads)(await upload_res.text())

            upload_url = upload['response']['upload_url']
            upload_photos = {}
            photo_order = []
            for i, photo in await sync_to_async(enumerate)(photo_sequence_part, start=1):
                photo_order.append(photo)
                image_link = photo.image.path if settings.DEBUG else photo.image.url
                upload_photos.update({f'file{i}': open(image_link, 'rb')})
            async with session.post(upload_url, data=upload_photos) as res:
                saving_photos = await sync_to_async(json.loads)(await res.text())
            for closed_file in upload_photos.values():
                closed_file.close()

            async with session.post(photos_save_url, params={
                **params,
                'album_id': vk_album_id,
                'group_id': settings.VK_GROUP_ID,
                'server': saving_photos['server'],
                'photos_list': saving_photos['photos_list'],
                'hash': saving_photos['hash'],
            }) as res:
                photos = await sync_to_async(json.loads)(await res.text())

            if photos.get('response'):
                for photo, photo_instance in zip(photos['response'], photo_order):
                    attachment = f'photo{photo["owner_id"]}_{photo["id"]}'
                    photo_instance.image_vk_id = attachment
                    await sync_to_async(photo_instance.save)()


async def delete_photos(photo_instance):
    """Удаление одной фотографии из альбома группы ВК"""

    delete_photos_url = 'https://api.vk.com/method/photos.delete'
    params = {'access_token': settings.VK_USER_TOKEN, 'v': '5.131'}
    photo_id = photo_instance.image_vk_id.split('_')[1]
    async with aiohttp.ClientSession() as session:
        async with session.post(
                delete_photos_url,
                params={**params, 'owner_id': f"-{settings.VK_GROUP_ID}", 'photo_id': photo_id}):
            pass


async def delete_album(album_instance):
    """Удаление альбома группы ВК"""

    delete_album_url = 'https://api.vk.com/method/photos.deleteAlbum'
    params = {'access_token': settings.VK_USER_TOKEN, 'v': '5.131'}
    album_id = album_instance.vk_album_id
    async with aiohttp.ClientSession() as session:
        async with session.post(
                delete_album_url,
                params={**params, 'group_id': settings.VK_GROUP_ID, 'album_id': album_id}) as response:
            pass


async def make_main_album_photo(vk_album_id, photo_id):
    """Назначение обложки альбома VK"""

    photos_makeсover_url = 'https://api.vk.com/method/photos.makeCover'
    params = {
        'access_token': settings.VK_USER_TOKEN,
        'v': '5.131',
        'owner_id': '-' + str(settings.VK_GROUP_ID),
        'photo_id': photo_id,
        'album_id': str(vk_album_id),
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(photos_makeсover_url, params=params):
            pass


async def get_group_albums(owner_id: str, /) -> dict:
    get_group_albums_url = 'https://api.vk.com/method/photos.getAlbums'
    params = {
        'access_token': settings.VK_USER_TOKEN,
        'v': '5.131',
        'owner_id': owner_id,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(get_group_albums_url, params=params) as response:
            return await sync_to_async(json.loads)(await response.text())


async def get_album_photos(owner_id: str, album_id: str, /) -> dict:
    get_album_photos_url = 'https://api.vk.com/method/photos.get'
    params = {
        'access_token': settings.VK_USER_TOKEN,
        'v': '5.131',
        'owner_id': owner_id,
        'album_id': album_id,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(get_album_photos_url, params=params) as response:
            return await sync_to_async(json.loads)(await response.text())
