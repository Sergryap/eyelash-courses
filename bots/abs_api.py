import aiohttp
import redis
import json

from abc import ABC, abstractmethod
from asgiref.sync import sync_to_async
from django.utils import timezone
from courses.models import Course, Office, Client


class AbstractAPI(ABC):

    @abstractmethod
    def __init__(self, redis_db: redis.Redis, session: aiohttp.ClientSession = None, loop=None):
        self.session = session
        self.redis_db = redis_db
        self.loop = loop
        self.sending_tasks = None

    @staticmethod
    @abstractmethod
    async def create_key_task(*args, **kwarg):
        pass

    @abstractmethod
    async def send_message(self, *args, **kwargs):
        pass

    @abstractmethod
    async def send_message_later(self, *args, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    async def create_reminder_text(first_name: str, course: Course, office: Office):
        pass

    @abstractmethod
    async def create_message_sending_tasks(self, *args, **kwargs):
        pass

    @abstractmethod
    async def update_message_sending_tasks(self, *args, **kwargs):
        pass

    @abstractmethod
    async def delete_message_sending_tasks(self, *args, **kwargs):
        pass

    async def update_tasks_triggered_admin(self, key_trigger):
        """Обновление отложенных задач отправки, если были изменения в админ-панели"""

        if self.redis_db.get(key_trigger) and int(self.redis_db.get(key_trigger)):
            if self.sending_tasks:
                for __, task in self.sending_tasks.items():
                    task.cancel()
                self.sending_tasks.clear()
            await self.update_message_sending_tasks()
            self.redis_db.delete(key_trigger)

    @abstractmethod
    async def update_message_single_sending_task(
            self,
            course: Course,
            client: Client,
            office: Office,
            interval,
            remind_before
    ):
        pass

    async def update_course_tasks_triggered_admin(self, key_trigger: str):
        if not self.redis_db.get(key_trigger):
            return
        data_update_tasks = json.loads(self.redis_db.get(key_trigger))
        self.redis_db.delete(key_trigger)
        if data_update_tasks['deleted_tasks']:
            for task_name in data_update_tasks['deleted_tasks']:
                if self.sending_tasks.get(task_name):
                    self.sending_tasks[task_name].cancel()
                    del self.sending_tasks[task_name]
        for course_pk in data_update_tasks['course_pks']:
            course = await sync_to_async(Course.objects.filter)(pk=course_pk)
            courses_prefetch = await sync_to_async(course.prefetch_related)('clients', 'reminder_intervals')
            course_of_tasks = await sync_to_async(courses_prefetch.first)()
            clients = await sync_to_async(course_of_tasks.clients.all)()
            if not clients:
                return
            reminder_intervals = await sync_to_async(course_of_tasks.reminder_intervals.all)()
            office = await Office.objects.async_first()
            time_to_start = (course_of_tasks.scheduled_at - timezone.now()).total_seconds()
            time_offset = 5 * 3600
            for remind_before in reminder_intervals:
                interval = time_to_start - time_offset - remind_before.reminder_interval * 3600
                if interval < 0:
                    continue
                for client in clients:
                    await self.update_message_single_sending_task(
                        course_of_tasks, client, office, interval, remind_before
                    )
