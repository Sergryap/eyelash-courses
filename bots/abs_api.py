import aiohttp
import redis
import json
import asyncio
import os
import random

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

    @staticmethod
    async def __mark_task_in_db(task_name: str) -> bool:
        """
        Делает пометку в БД о выполнении таймера задачи.
        task_name должна иметь формат {Task.task_name}:{Task.timers[i]}
        """

        group_task_name, timer = task_name.split(':')
        instance_task = await Task.objects.aget(task_name=group_task_name)
        instance_task.call_counter += 1
        if instance_task.call_counter > len(instance_task.timers):
            return False
        completed_timers = instance_task.completed_timers
        if [int(timer)] in completed_timers:
            return False
        instance_task.completed_timers = completed_timers + [int(timer)]
        await sync_to_async(instance_task.save)()
        return True

    async def schedule_task(
            self,
            task_name: str,
            schedule_func: str,
            current_timer: int,
            mark_to_db: bool,
            /,
            *args, **kwargs,
    ) -> asyncio.Task:
        """
        Создание отложенной задачи из schedule_func.
        Если mark_to_db=True, то task_name должна иметь формат {Task.task_name}:{Task.timers[i]} и
        в этом случае делается пометка в базе данных о выполнении задачи
        """

        async def coro() -> None:
            await asyncio.sleep(current_timer)
            mark_task_flag = await self.__mark_task_in_db(task_name)
            if mark_to_db and not mark_task_flag:
                return
            await getattr(self, schedule_func)(*args, **kwargs)
            del self.sending_tasks[task_name]
        return asyncio.ensure_future(coro(), loop=self.loop)

    async def __get_database_bypass_timer(
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
            hour_interval: int = 0,
            hours: Union[List[Union[int, str]], Tuple[Union[int, str]]] = (1, 5, 10, 22),
            minute_offset: int = 0
    ):
        """
        Создание задач из таблицы Task базы данных
        Если задачи в конкретном экземпляре таблицы БД выполнены,
        т.е. task.call_counter >= len(json.loads(task.timers)),
        то задача заново не создается.
        Если таймер отработал, т.е. timer in json.loads(task.completed_timers),
        то задача тоже не создается.
        Для разового запуска использовать force=True
        timer берет отсчет от момента регистрации пользователя
        """
        async def coro():
            second_offset = minute_offset * 60
            first_timer = random.randint(10, 20)
            while True:
                start_timer = hour_interval * 3600 or await self.__get_database_bypass_timer(hours=hours)
                if first_timer:
                    start_timer = first_timer
                    first_timer = 0
                elif second_offset and hour_interval:
                    start_timer += second_offset
                    second_offset = 0
                print(f'До ближайшего обхода таблицы Task: {start_timer} c.')
                await asyncio.sleep(start_timer)
                tasks = await sync_to_async(Task.objects.all)()
                for task in tasks:
                    if task.call_counter >= len(task.timers):
                        await sync_to_async(task.delete)()
                        continue
                    for timer in task.timers:
                        task_name = f'{task.task_name}:{timer}'
                        if self.sending_tasks.get(task_name):
                            continue
                        if timer in task.completed_timers:
                            continue
                        args = task.args
                        kwargs = task.kwargs
                        client = (
                            await Client.objects.async_filter(telegram_id=args[0]) or
                            await Client.objects.async_filter(vk_id=args[0])
                        )
                        if not client:
                            continue
                        current_client = await sync_to_async(client.first)()
                        if not (
                            current_client.vk_id and hasattr(self, 'vk_group_id') or
                            current_client.telegram_id and not hasattr(self, 'vk_group_id')
                        ):
                            continue
                        registered_at = current_client.registered_at
                        current_time = timezone.now() + timezone.timedelta(hours=self.hour_offset)
                        current_timer = timer - (current_time - registered_at).total_seconds()
                        print(current_timer)
                        if current_timer < 0:
                            task.completed_timers.append(int(timer))
                            task.call_counter += 1
                            await sync_to_async(task.save)()
                            continue
                        real_task = await self.schedule_task(
                            task_name,
                            task.coro,
                            int(current_timer),
                            True,
                            *args, **kwargs,
                        )
                        self.sending_tasks.update({task_name: real_task})
                if force:
                    break
        asyncio.ensure_future(coro(), loop=self.loop)

    @staticmethod
    async def convert_template_to_message(template: str, convert_keys: dict) -> str:
        message = template
        for key, value in convert_keys.items():
            keys = ['{' + key + '}', '{ ' + key + '}', '{' + key + ' }', '{ ' + key + ' }']
            for real_key in keys:
                if real_key in message:
                    message = message.replace(real_key, value)
                    continue
        return message

    async def bypass_users_to_create_tasks(
            self,
            force: bool = False,
            hour_interval: int = 0,
            hours: Union[List[Union[int, str]], Tuple[Union[int, str]]] = (10, 23),
            minute_offset: int = 0
    ):
        """
        Создает задачи для пользователей, в зависимости от их записей на курсы,
        создавая или удаляя записи в таблице Task БД
        """
        async def coro():
            second_offset = minute_offset * 60
            first_timer = 2
            while True:
                start_timer = 1 if force else hour_interval * 3600 or await self.__get_database_bypass_timer(hours=hours)
                if first_timer:
                    start_timer = first_timer
                    first_timer = 0
                elif second_offset and hour_interval:
                    start_timer += second_offset
                    second_offset = 0
                print(f'До ближайшего обхода таблицы Client: {start_timer} c.')
                await asyncio.sleep(start_timer)
                users = await Client.objects.async_all()
                users_prefetch_courses = await sync_to_async(users.prefetch_related)('courses')
                past_courses = await Course.objects.async_filter(
                    scheduled_at__lte=timezone.now() + timezone.timedelta(hours=self.hour_offset),
                    published_in_bot=True
                )
                past_courses_prefetch_clients = await sync_to_async(past_courses.prefetch_related)('clients')
                with open(os.path.join(os.getcwd(), 'bots', 'step_messages.json')) as file:
                    msg_steps = json.load(file)
                for user in users_prefetch_courses:
                    task_name_prefix = {
                        user.telegram_id: 'tg_send_no_courses',
                        user.vk_id: 'vk_send_no_courses'
                    }
                    user_id = user.telegram_id or user.vk_id
                    task_name_start = f'{task_name_prefix[user_id]}_{user_id}'
                    if not await sync_to_async(user.courses.all)():
                        await self.create_single_step_task(user, task_name_start, msg_steps['No_courses'])
                    else:
                        task_queryset = await Task.objects.async_filter(task_name__istartswith=task_name_start)
                        if task_name_start in user.completed_tasks:
                            user.completed_tasks.remove(task_name_start)
                            await sync_to_async(user.save)()
                        for db_task in task_queryset:
                            real_tasks = (
                                f'{task_name_start}_{msg["timer"]}:{timer}'
                                for timer in db_task.timers
                                for msg in msg_steps['No_courses']
                            )
                            for real_task_name in real_tasks:
                                if self.sending_tasks.get(real_task_name):
                                    self.sending_tasks[real_task_name].cancel()
                                    del self.sending_tasks[real_task_name]
                            await sync_to_async(db_task.delete)()
                        for course in past_courses_prefetch_clients:
                            if user in await sync_to_async(course.clients.all)():
                                print('Задача для пользователей, которые проходили курсы')
                if force:
                    break
        asyncio.ensure_future(coro(), loop=self.loop)

    async def create_single_step_task(
            self,
            user: Client,
            task_name_start: str,
            step_messages: List[Dict[str, Union[str, int]]],
            start_timer: int = 200
    ):
        registered_at = user.registered_at
        current_time = timezone.now() + timezone.timedelta(hours=self.hour_offset)
        for msg in step_messages:
            timer = int((current_time - registered_at).total_seconds() + msg['timer'] + start_timer)
            args = [
                user.telegram_id or user.vk_id,
                await self.convert_template_to_message(msg['msg'], {"first_name": user.first_name})
            ]
            kwargs = dict()
            if user.vk_id:
                button = [[{
                    'action': {'type': 'text', 'payload': {'button': 'start'}, 'label': '☰ MENU'},
                    'color': 'secondary'
                }]]
                keyboard = {'inline': True, 'buttons': button}
                kwargs.update(keyboard=json.dumps(keyboard, ensure_ascii=False))
            await Task.objects.async_get_or_create(
                task_name=f'{task_name_start}_{msg["timer"]}',
                defaults={
                    'coro': 'send_message',
                    'timers': [timer],
                    'completed_timers': list(),
                    'args': args,
                    'kwargs': kwargs
                }
            )
        if task_name_start not in user.completed_tasks:
            user.completed_tasks.append(task_name_start)
            await sync_to_async(user.save)()

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
            if not course_of_tasks:
                continue
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
