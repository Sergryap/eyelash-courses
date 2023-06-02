import asyncio
import json
import aiohttp
import redis

from bots.abs_api import AbstractAPI
from asgiref.sync import sync_to_async
from django.utils import timezone
from courses.models import Course, Office, Timer, Client
from typing import Dict, Union, Tuple, List
from textwrap import dedent


class TgApi(AbstractAPI):
    """Класс API методов Tg"""
    def __init__(self, tg_token: str, redis_db: redis.Redis, session: aiohttp.ClientSession = None, loop=None):
        super().__init__(redis_db, session, loop)
        self.token = tg_token

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

    async def loop_send_message(self, chat_id, msg, *, reply_markup=None, parse_mode=None, interval: int):

        while True:
            await self.send_message(chat_id, msg, reply_markup=reply_markup, parse_mode=parse_mode)
            await asyncio.sleep(interval * 60)

    async def send_multiple_messages(
            self,
            chat_id,
            messages: Union[List[str], Tuple[str]],
            timers: Union[List[int], Tuple[int]],
            reply_markups: Union[List[Union[str, None]], Tuple[Union[str, None]]] = None,
            parse_modes: Union[List[Union[str, None]], Tuple[Union[str, None]]] = None,

    ) -> None:
        """Отправка сообщения через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendmessage"

        iterate_data = zip(
            messages,
            timers,
            reply_markups or [None] * len(timers),
            parse_modes or [None] * len(timers)
        )
        for msg, timer, reply_markup, parse_mode in iterate_data:
            params = {
                'chat_id': chat_id,
                'text': msg,
                'reply_markup': reply_markup,
                'parse_mode': parse_mode
            }
            await asyncio.sleep(timer)
            for param, value in params.copy().items():
                if value is None:
                    del params[param]
            async with self.session.get(url, params=params) as res:
                res.raise_for_status()

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

    async def schedule_send_message_task(
            self,
            chat_id: int,
            msg: str,
            /,
            task_name: str,
            interval: int = None,
            time_offset: int = None,
            time_to_start: int = None,
            remind_before: int = None,
            reply_markup=None,
            parse_mode=None,
    ) -> asyncio.Task | None:
        """
        Отложенная отправка сообщения с использованием schedule_task
        !!! Функция не используется и требует доработки
        """

        timer = interval if interval else time_to_start - time_offset - remind_before
        if timer < 0:
            return
        return await self.schedule_task(
            task_name,
            'send_message',
            timer,
            chat_id,
            msg,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

    async def send_message_later(
            self,
            chat_id,
            msg,
            /,
            task_name,
            interval: int = None,
            time_offset: int = None,
            time_to_start: int = None,
            remind_before: int = None,
            reply_markup=None,
            parse_mode=None,
    ) -> Union[asyncio.Task, None]:
        """Отложенная отправка сообщения"""
        timer = interval if interval else time_to_start - time_offset - remind_before
        if timer < 0:
            return

        async def coro():
            await asyncio.sleep(timer)
            await self.send_message(chat_id, msg, reply_markup=reply_markup, parse_mode=parse_mode)
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
        if not client.telegram_id:
            return
        task_name = await self.create_key_task(client.telegram_id, course.pk, remind_before)
        text = await self.create_reminder_text(client.first_name, course, office)
        task = await self.send_message_later(
            client.telegram_id,
            dedent(text),
            interval=interval,
            parse_mode='Markdown',
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
                    if not client.telegram_id:
                        continue
                    text = await self.create_reminder_text(client.first_name, course, office)
                    msg = reminder_text if reminder_text else text
                    task_name = await self.create_key_task(client.telegram_id, course.pk, remind_before)
                    task = await self.send_message_later(
                        client.telegram_id,
                        dedent(msg),
                        interval=interval,
                        parse_mode='Markdown',
                        task_name=task_name
                    )
                    self.sending_tasks.update({task_name: task})
        return self.sending_tasks

    async def delete_message_sending_tasks(self, course_pk, chat_id):
        """Удаляет отложенные задачи оповещения для заданного course_pk и chat_id"""

        course = await sync_to_async(Course.objects.filter)(pk=course_pk)
        courses_prefetch = await sync_to_async(course.prefetch_related)('reminder_intervals')
        course_of_deletion_tasks = await sync_to_async(courses_prefetch.first)()
        reminder_intervals = await sync_to_async(course_of_deletion_tasks.reminder_intervals.all)()
        for remind_before in reminder_intervals:
            task_name = await self.create_key_task(chat_id, course_pk, remind_before)
            if self.sending_tasks.get(task_name):
                self.sending_tasks[task_name].cancel()
                del self.sending_tasks[task_name]

    async def create_message_sending_tasks(self, course_pk, chat_id, *, reminder_text: str):
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
            task_name = await self.create_key_task(chat_id, course_pk, remind_before)
            task = await self.send_message_later(
                chat_id,
                dedent(reminder_text),
                interval=interval,
                parse_mode='Markdown',
                task_name=task_name
            )
            if self.sending_tasks.get(task_name):
                self.sending_tasks[task_name].cancel()
            self.sending_tasks[task_name] = task

    @staticmethod
    async def create_key_task(chat_id, course_pk, remind_before: Timer | int) -> str:
        if isinstance(remind_before, Timer):
            remind_before_reminder_interval = remind_before.reminder_interval
        else:
            remind_before_reminder_interval = remind_before
        return f'remind_record_tg_{chat_id}_{course_pk}_{remind_before_reminder_interval}'

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
