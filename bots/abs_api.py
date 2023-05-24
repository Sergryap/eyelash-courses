import aiohttp
import redis
import json
import asyncio

from abc import ABC, abstractmethod
from asgiref.sync import sync_to_async
from django.utils import timezone
from courses.models import Course, Office, Client, Task
from typing import Tuple, List, Dict, Union


class AbstractAPI(ABC):

    @abstractmethod
    def __init__(self, redis_db: redis.Redis, session: aiohttp.ClientSession = None, loop=None, hour_offset=5):
        self.session = session
        self.redis_db = redis_db
        self.loop = loop
        self.sending_tasks = None
        self.hour_offset = hour_offset

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

    async def schedule_task(
            self,
            task_name: str,
            schedule_func: str,
            current_timer: int,
            /,
            *args, **kwargs,
    ) -> asyncio.Task:
        """
        Создание отложенной задачи из schedule_func для именованной группы задач group_task_name
        task_name должна иметь формат {Task.task_name}__{Task.timers[i]}
        """

        async def coro() -> None:
            await asyncio.sleep(current_timer)
            group_task_name, timer = task_name.split('__')
            instance_task = await Task.objects.aget(task_name=group_task_name)
            instance_task.call_counter += 1
            if instance_task.call_counter > len(json.loads(instance_task.timers)):
                return
            instance_task.completed_timers = json.dumps(json.loads(instance_task.completed_timers) + [int(timer)])
            await sync_to_async(instance_task.save)()
            await getattr(self, schedule_func)(*args, **kwargs)
            del self.sending_tasks[task_name]
        return asyncio.ensure_future(coro(), loop=self.loop)

    async def get_database_bypass_timer(
            self,
            hours: Union[List[Union[int, str]], Tuple[Union[int, str]]]
    ) -> float:
        """
        Получение таймера для ближайшего обновления задач
        times: список часов для обновления в течение дня
        """

        today = timezone.datetime.now() + timezone.timedelta(hours=self.hour_offset)

        for hour in sorted(hours):
            timer = timezone.datetime.strptime(f'{today.date()} {str(hour)}:00:00', '%Y-%m-%d %H:%M:%S') - today
            if timer.total_seconds() > 0:
                return int(timer.total_seconds())
        end_time_delta = (24 - int(sorted(hours)[-1])) * 3600
        end_time = timezone.datetime.strptime(f'{today.date()} {str(sorted(hours)[-1])}', '%Y-%m-%d %H')
        current_delta = (today - end_time).total_seconds()
        first_time_delta = int(sorted(hours)[0]) * 3600
        return int(end_time_delta + first_time_delta - current_delta)

    async def create_tasks_from_db(
            self,
            force: bool = False,
            timers: Union[List[Union[int, str]], Tuple[Union[int, str]]] = (1, 5, 10, 22)
    ):
        """
        Создание задач из таблицы Task базы данных
        Если задачи в конкретном экземпляре таблицы БД выполнены,
        т.е. task.call_counter >= len(json.loads(task.timers)),
        то задача заново не создается.
        Если таймер отработал, т.е. timer in json.loads(task.completed_timers),
        то задача тоже не создается.
        Для разового запуска использовать force=True
        """
        async def coro():
            while True:
                start_timer = 1 if force else await self.get_database_bypass_timer(hours=timers)
                print(f'До ближайшего обхода: {start_timer} c.')
                await asyncio.sleep(start_timer)
                tasks = await sync_to_async(Task.objects.all)()
                for task in tasks:
                    if task.call_counter >= len(json.loads(task.timers)):
                        continue
                    msg = [task.message] if task.message else []
                    for timer in json.loads(task.timers):
                        task_name = f'{task.task_name}__{timer}'
                        if self.sending_tasks.get(task_name):
                            continue
                        if timer in json.loads(task.completed_timers):
                            continue
                        args = json.loads(task.args)
                        kwargs = json.loads(task.kwargs)
                        client = (
                            await Client.objects.async_filter(telegram_id=args[0]) or
                            await Client.objects.async_filter(vk_id=args[0])
                        )
                        current_client = await sync_to_async(client.first)()
                        registered_at = current_client.registered_at
                        today = timezone.now() + timezone.timedelta(hours=self.hour_offset)
                        current_timer = timer - (today - registered_at).total_seconds()
                        print(current_timer)
                        if current_timer < 0:
                            task.completed_timers = json.dumps(json.loads(task.completed_timers) + [int(timer)])
                            task.call_counter += 1
                            await sync_to_async(task.save)()
                            continue

                        real_task = await self.schedule_task(
                            task_name,
                            task.coro,
                            int(current_timer),
                            *(args + msg),
                            **kwargs
                        )
                        self.sending_tasks.update({task_name: real_task})
                if force:
                    break
        asyncio.ensure_future(coro(), loop=self.loop)

    @staticmethod
    async def get_or_create_task_to_db(
            group_task_name: str,
            coro: str,
            timers: List[int],
            message: str,
            args: List,
            kwargs: Dict

    ):
        await Task.objects.async_get_or_create(
            task_name=group_task_name,
            defaults={
                'coro': coro,
                'timers': json.dumps(timers),
                'message': message,
                'args': json.dumps(args),
                'kwargs': json.dumps(kwargs)
            }
        )

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
