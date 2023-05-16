import asyncio
import json
import aiohttp
import redis

from asgiref.sync import sync_to_async
from django.utils import timezone
from courses.models import Course, Office
from typing import Dict
from textwrap import dedent


class TgApi:
    """Класс API методов Tg"""
    def __init__(self, tg_token: str, redis_db: redis.Redis, session: aiohttp.ClientSession = None, loop=None):
        self.session = session
        self.token = tg_token
        self.redis_db = redis_db
        self.loop = loop
        self.sending_tasks = None

    async def send_message(self, chat_id, msg, *, reply_markup=None, parse_mode=None):
        """Отправка сообщения через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendmessage"
        params = {
            'chat_id': chat_id,
            'text': msg,
            'reply_markup': reply_markup,
            'parse_mode': parse_mode
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    @staticmethod
    async def create_reminder_text(first_name: str, course: Course, office: Office) -> str:
        return f'''
             {first_name}, напоминаем,
             что вы записаны на курс:
             *{course.name.upper()}*
             _Дата курса: {course.scheduled_at.strftime("%d.%m.%Y")}._
             _Время начала: {course.scheduled_at.strftime("%H:%M")}._
             _Адрес: {office.address}_
             _Спасибо, что выбрали нашу школу._
             _Будем рады вас видеть!_
             '''

    async def send_message_later(
            self,
            chat_id,
            msg,
            /,
            interval: int = None,
            time_offset: int = None,
            time_to_start: int = None,
            remind_before: int = None,
            reply_markup=None,
            parse_mode=None
    ) -> asyncio.Task:
        """Отложенная отправка сообщения"""
        timer = interval if interval else time_to_start - time_offset - remind_before

        async def coro():
            await asyncio.sleep(timer)
            await self.send_message(chat_id, msg, reply_markup=reply_markup, parse_mode=parse_mode)
        return asyncio.ensure_future(coro(), loop=self.loop)

    async def update_message_sending_tasks(
            self,
            time_offset: int = 5 * 3600,
            remind_before: int = 86400 - 6 * 3600,
            reminder_text: str = None
    ) -> Dict[str, asyncio.Task]:

        """Создание отложенных задач по отправке сообщений пользователям по данным базы данных"""

        future_courses = await Course.objects.async_filter(scheduled_at__gt=timezone.now(), published_in_bot=True)
        future_courses_prefetch = await sync_to_async(future_courses.prefetch_related)('clients')
        office = await Office.objects.async_first()
        tasks = {}
        for course in future_courses_prefetch:
            clients = await sync_to_async(course.clients.all)()
            time_to_start = (course.scheduled_at - timezone.now()).total_seconds()
            interval = time_to_start - time_offset - remind_before
            if interval < 0:
                continue
            for client in clients:
                if not client.telegram_id:
                    continue
                text = await self.create_reminder_text(client.first_name, course, office)
                msg = reminder_text if reminder_text else text
                name_task = f'remind_record_tg_{client.telegram_id}_{course.pk}'
                task = await self.send_message_later(
                    client.telegram_id,
                    dedent(msg),
                    interval=interval,
                    parse_mode='Markdown'
                )
                tasks.update({name_task: task})
        return tasks

    async def send_location(self, chat_id, *, lat, long, reply_markup=None):
        """Отправка локации через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendlocation"
        params = {
            'chat_id': chat_id,
            'latitude': lat,
            'longitude': long,
            'reply_markup': reply_markup
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def send_photo(self, chat_id, *, photo, caption=None, reply_markup=None, parse_mode=None):
        """Отправка фото через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendphoto"
        params = {
            'chat_id': chat_id,
            'caption': caption,
            'reply_markup': reply_markup,
            'photo': photo,
            'parse_mode': parse_mode
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def send_venue(self, chat_id, *, lat, long, title, address, reply_markup=None):
        """Отправка события через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendvenue"
        params = {
            'chat_id': chat_id,
            'latitude': lat,
            'longitude': long,
            'title': title,
            'address': address,
            'reply_markup': reply_markup
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def send_media_group(self, chat_id, *, media: list):
        """Отправка нескольких медиа через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendmediagroup"
        params = {
            'chat_id': chat_id,
            'media': json.dumps(media)
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def answer_callback_query(self, callback_query_id: str, text: str):
        """Отправка уведомления в виде всплывающего сообщения"""
        url = f"https://api.telegram.org/bot{self.token}/answercallbackquery"
        params = {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': 1
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def edit_message_reply_markup(self, chat_id, message_id, reply_markup):
        """Изменение существующей клавиатуры"""
        url = f"https://api.telegram.org/bot{self.token}/editmessagereplymarkup"
        params = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reply_markup': reply_markup
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def delete_message(self, chat_id, message_id):
        """Удаление существующей клавиатуры"""
        url = f"https://api.telegram.org/bot{self.token}/deletemessage"
        params = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())


class TgEvent:
    def __init__(self, event):
        if event.get('message'):
            event_info = event['message']
            chat_event_info = event_info['chat']
            self.user_reply = event_info['text']
            self.chat_id = chat_event_info['id']
            self.first_name = chat_event_info['first_name']
            self.last_name = chat_event_info.get('last_name', '')
            self.username = chat_event_info.get('username', '')
            self.message_id = event_info['message_id']
            self.callback_query = False
            self.message = True

        elif event.get('callback_query'):
            event_info = event['callback_query']
            chat_event_info = event_info['message']['chat']
            self.user_reply = event_info['data']
            self.chat_id = chat_event_info['id']
            self.first_name = chat_event_info['first_name']
            self.last_name = chat_event_info.get('last_name', '')
            self.username = chat_event_info.get('username', '')
            self.callback_query_id = event_info['id']
            self.message_id = event_info['message']['message_id']
            self.callback_query = True
            self.message = False

        # elif
        # При необходимости добавить новые типы событий
        # return

        else:
            self.unknown_event = True
