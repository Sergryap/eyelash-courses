import json
import asyncio
import aiohttp
import requests
import redis
import random

from bots.abs_api import AbstractAPI
from more_itertools import chunked
from asgiref.sync import sync_to_async
from django.utils import timezone
from courses.models import Course, Office, Timer, Client
from typing import Dict, Union
from textwrap import dedent
from .buttons import get_menu_button
from typing import Dict, Union, Tuple, List


class VkApi(AbstractAPI):
    """Класс API методов Vk"""
    def __init__(
            self,
            vk_group_token: str = None,
            vk_user_token: str = None,
            vk_group_id: int = None,
            redis_db: redis.Redis = None,
            session: aiohttp.ClientSession = None,
            loop=None
    ):
        super().__init__(redis_db, session, loop)
        self.token = vk_group_token
        self.user_token = vk_user_token
        self.vk_group_id = vk_group_id

    async def send_message(
            self,
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
            'access_token': self.token, 'v': '5.131',
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
        async with self.session.post(send_message_url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def loop_send_message(self, user_id: int, message: str, *, keyboard: str = None, interval: int):

        while True:
            await self.send_message(user_id, message, keyboard=keyboard)
            await asyncio.sleep(interval * 60)

    async def send_multiple_messages(
            self,
            user_id,
            messages: Union[List[str], Tuple[str]],
            timers: Union[List[int], Tuple[int]],
            keyboards: Union[List[Union[str, None]], Tuple[Union[str, None]]] = None,
    ) -> None:
        send_message_url = 'https://api.vk.com/method/messages.send'
        iterate_data = zip(
            messages,
            timers,
            keyboards or [None] * len(timers)
        )
        for msg, timer, keyboard in iterate_data:
            params = {
                'access_token': self.token, 'v': '5.131',
                'user_id': user_id,
                'random_id': random.randint(0, 1000),
                'message': msg,
                'keyboard': keyboard,
            }
            for param, value in params.copy().items():
                if value is None:
                    del params[param]
            await asyncio.sleep(timer)
            async with self.session.get(send_message_url, params=params) as res:
                res.raise_for_status()

    @staticmethod
    async def create_reminder_text(name: str, course: Course, office: Office) -> str:
        return f'''
            {name}, напоминаем,
            что вы записаны на курс:
            **{course.name.upper()}**
            Дата курса: {course.scheduled_at.strftime("%d.%m.%Y")}.
            Время начала: {course.scheduled_at.strftime("%H:%M")}.
            Адрес: {office.address}
            Спасибо, что выбрали нашу школу.
            Будем рады вас видеть!
            '''

    async def send_message_later(
            self,
            user_id: int,
            message: str,
            /,
            task_name,
            interval: int = None,
            time_offset: int = 5 * 3600,
            time_to_start: int = None,
            remind_before: int = 86400 - 6 * 3600,
            user_ids: str = None,
            keyboard: str = None,
            attachment: str = None,
            payload: str = None,
            sticker_id: int = None,
            lat: str = None,
            long: str = None,
    ) -> Union[asyncio.Task, None]:
        """Отложенная отправка сообщения"""

        timer = interval if interval else time_to_start - time_offset - remind_before
        if timer < 0:
            return

        async def coro():
            await asyncio.sleep(timer)
            await self.send_message(
                user_id,
                message,
                user_ids,
                keyboard,
                attachment,
                payload,
                sticker_id,
                lat,
                long,
            )
            del self.sending_tasks[task_name]
        return asyncio.ensure_future(coro(), loop=self.loop)

    async def update_message_single_sending_task(
            self,
            course: Course,
            client: Client,
            office: Office,
            interval: int,
            remind_before: Timer
    ):
        if not client.vk_id:
            return
        task_name = await self.create_key_task(client.vk_id, course.pk, remind_before)
        text = await self.create_reminder_text(client.first_name, course, office)
        task = await self.send_message_later(
            client.vk_id,
            dedent(text),
            interval=interval,
            keyboard=await get_menu_button(color='secondary', inline=True),
            task_name=task_name
        )
        if self.sending_tasks.get(task_name):
            self.sending_tasks[task_name].cancel()
            del self.sending_tasks[task_name]
        self.sending_tasks.update({task_name: task})

    async def update_message_sending_tasks(
            self,
            time_offset: int = 5 * 3600,
            reminder_text: str = None
    ) -> Dict[str, asyncio.Task]:

        """Создание отложенных задач по отправке сообщений пользователям по данным базы данных"""

        future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now(), published_in_bot=True)
        future_courses_prefetch = await sync_to_async(future_courses.prefetch_related)('clients', 'reminder_intervals')
        office = await Office.objects.async_first()
        if self.sending_tasks:
            self.sending_tasks.clear()
        self.sending_tasks = {}
        for course in future_courses_prefetch:
            reminder_intervals = await sync_to_async(course.reminder_intervals.all)()
            time_to_start = (course.scheduled_at - timezone.now()).total_seconds()
            clients = await sync_to_async(course.clients.all)()
            if not clients:
                return self.sending_tasks
            for remind_before in reminder_intervals:
                interval = time_to_start - time_offset - remind_before.reminder_interval * 3600
                if interval < 0:
                    continue
                for client in clients:
                    if not client.vk_id:
                        continue
                    text = await self.create_reminder_text(client.first_name, course, office)
                    msg = reminder_text if reminder_text else text
                    task_name = await self.create_key_task(client.vk_id, course.pk, remind_before)
                    task = await self.send_message_later(
                        client.vk_id,
                        dedent(msg),
                        interval=interval,
                        keyboard=await get_menu_button(color='secondary', inline=True),
                        task_name=task_name
                    )
                    self.sending_tasks.update({task_name: task})
        return self.sending_tasks

    async def delete_message_sending_tasks(self, course_pk, user_id):
        """Удаляет отложенные задачи оповещения для заданного course_pk и chat_id"""
        course = await sync_to_async(Course.objects.filter)(pk=course_pk)
        courses_prefetch = await sync_to_async(course.prefetch_related)('reminder_intervals')
        course_of_deletion_tasks = await sync_to_async(courses_prefetch.first)()
        reminder_intervals = await sync_to_async(course_of_deletion_tasks.reminder_intervals.all)()
        for remind_before in reminder_intervals:
            task_name = await self.create_key_task(user_id, course_pk, remind_before)
            if self.sending_tasks.get(task_name):
                self.sending_tasks[task_name].cancel()
                del self.sending_tasks[task_name]

    async def create_message_sending_tasks(self, course_pk, user_id, *, reminder_text: str):
        """Создает отложенные задачи оповещения для заданного course_pk и chat_id"""
        course = await sync_to_async(Course.objects.filter)(pk=course_pk)
        courses_prefetch = await sync_to_async(course.prefetch_related)('reminder_intervals')
        course_of_creation_tasks = await sync_to_async(courses_prefetch.first)()
        reminder_intervals = await sync_to_async(course_of_creation_tasks.reminder_intervals.all)()
        time_to_start = (course_of_creation_tasks.scheduled_at - timezone.now()).total_seconds()
        time_offset = 5 * 3600
        for remind_before in reminder_intervals:
            interval = time_to_start - time_offset - remind_before.reminder_interval * 3600
            if interval < 0:
                continue
            task_name = await self.create_key_task(user_id, course_pk, remind_before)
            task = await self.send_message_later(
                user_id,
                dedent(reminder_text),
                interval=interval,
                task_name=task_name
            )
            if self.sending_tasks.get(task_name):
                self.sending_tasks[task_name].cancel()
            self.sending_tasks[task_name] = task

    @staticmethod
    async def create_key_task(user_id, course_pk, remind_before: Timer | int) -> str:
        if isinstance(remind_before, Timer):
            remind_before_reminder_interval = remind_before.reminder_interval
        else:
            remind_before_reminder_interval = remind_before
        return f'remind_record_vk_{user_id}_{course_pk}_{remind_before_reminder_interval}'

    async def get_user(self, user_ids: str):
        get_users_url = 'https://api.vk.com/method/users.get'
        params = {
            'access_token': self.token,
            'v': '5.131',
            'user_ids': user_ids
        }
        async with self.session.get(get_users_url, params=params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
            return response.get('response')

    def upload_photos_in_album(self, photo_instances, vk_album_id, /):
        """Загрузка фотографий в альбом группы ВК"""

        upload_server_url = 'https://api.vk.com/method/photos.getUploadServer'
        photos_save_url = 'https://api.vk.com/method/photos.save'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'album_id': vk_album_id,
            'group_id': self.vk_group_id
        }

        for photo_sequence_part in chunked(photo_instances, 5):
            upload_response = requests.get(url=upload_server_url, params=params)
            upload_response.raise_for_status()
            upload = upload_response.json()
            upload_url = upload['response']['upload_url']
            upload_photos = {}
            photo_order = []
            for i, photo in enumerate(photo_sequence_part, start=1):
                photo_order.append(photo)
                upload_photos.update({f'file{i}': open(photo.image.path, 'rb')})
            photo_response = requests.post(url=upload_url, files=upload_photos)
            saving_photos = photo_response.json()
            for closed_file in upload_photos.values():
                closed_file.close()

            res = requests.post(
                url=photos_save_url,
                params={
                    **params,
                    'server': saving_photos['server'],
                    'photos_list': saving_photos['photos_list'],
                    'hash': saving_photos['hash'],
                }
            )
            res.raise_for_status()
            photos = res.json()

            if photos.get('response'):
                for photo, photo_instance in zip(photos['response'], photo_order):
                    attachment = f'photo{photo["owner_id"]}_{photo["id"]}'
                    photo_instance.image_vk_id = attachment
                    photo_instance.save()

    def delete_photos(self, obj, /):
        """Удаление одной фотографии из альбома группы ВК"""

        delete_photos_url = 'https://api.vk.com/method/photos.delete'
        photo_id = obj.image_vk_id.split('_')[1]
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'owner_id': f"-{self.vk_group_id}",
            'photo_id': photo_id
        }
        res = requests.post(url=delete_photos_url, params=params)
        res.raise_for_status()

    def create_vk_album(self, obj, /):
        """Создание пустого альбома vk"""
        create_vk_album_url = 'https://api.vk.com/method/photos.createAlbum'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'title': obj.name,
            'group_id': self.vk_group_id,
            'description': obj.short_description,
            'upload_by_admins_only': 1,
        }
        response = requests.post(url=create_vk_album_url, params=params)
        response.raise_for_status()
        return response.json()

    def edit_vk_album(self, obj, /):
        """Редактирование существующего альбома VK"""

        edit_vk_album_url = 'https://api.vk.com/method/photos.editAlbum'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'album_id': str(obj.vk_album_id),
            'owner_id': '-' + str(self.vk_group_id),
            'title': obj.name,
            'description': obj.short_description,
            'upload_by_admins_only': 1,
        }
        res = requests.post(url=edit_vk_album_url, params=params)
        res.raise_for_status()

    def make_main_album_photo(self, vk_album_id, photo_id, /):
        """Назначение обложки альбома VK"""

        photos_makeсover_url = 'https://api.vk.com/method/photos.makeCover'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'owner_id': '-' + str(self.vk_group_id),
            'photo_id': photo_id,
            'album_id': str(vk_album_id),
        }
        res = requests.post(url=photos_makeсover_url, params=params)
        res.raise_for_status()
