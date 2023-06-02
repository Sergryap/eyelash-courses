import json

from typing import Union
from django.core.management import BaseCommand
from courses.models import Client, Task, ScheduledMessage, CourseClient, Course
from django.utils import timezone
from django.db.models import Q, QuerySet


class Command(BaseCommand):
    help = 'Создание записей в таблице Task базы данных для запланированных сообщений'

    def handle(self, *args, **options):
        messages = ScheduledMessage.objects.select_related('client')
        current_time = timezone.now() + timezone.timedelta(hours=5)
        clients = Client.objects.prefetch_related('courses')
        course_clients = CourseClient.objects.select_related('course', 'client')
        with_courses_clients = [user.client for user in course_clients]
        without_courses_clients = set(clients).difference(with_courses_clients)
        past_courses_clients = course_clients.filter(
            course__scheduled_at__lte=current_time,
            course__published_in_bot=True
        )
        future_courses_clients = course_clients.filter(
            course__scheduled_at__gt=current_time,
            course__published_in_bot=True
        )
        past_courses_no_future_clients = (
            course_clients.filter(
                course__scheduled_at__lte=current_time,
                course__published_in_bot=True
            ).filter(~Q(course__scheduled_at__gt=current_time))
        )
        fresh_time = current_time - timezone.timedelta(days=5)
        fresh_register_clients = Client.objects.filter(registered_at__gt=fresh_time)
        for message in messages:
            if message.client_status == 'all':
                create_db_tasks_for_clients(clients, message)
            elif message.client_status == 'no_courses':
                create_db_tasks_for_clients(without_courses_clients, message)
            elif message.client_status == 'past_courses':
                create_db_tasks_for_clients(past_courses_clients, message)
            elif message.client_status == 'future_courses':
                create_db_tasks_for_clients(future_courses_clients, message)
            elif message.client_status == 'past_courses_no_future':
                create_db_tasks_for_clients(past_courses_no_future_clients, message)
            elif message.client_status == 'fresh_register':
                create_db_tasks_for_clients(fresh_register_clients, message)
            elif message.client:
                create_db_tasks_for_clients({message.client}, message)


def create_db_task(
    user: Union[Client, CourseClient],
    task_name: str,
    message_template: str,
    start_timer: int,
    repeat: int = None
):
    client = user.client if isinstance(user, CourseClient) else user
    args = [
        client.telegram_id or client.vk_id,
        convert_template_to_message(message_template, {"first_name": client.first_name})
    ]
    kwargs = dict()
    if client.vk_id:
        button = [[{
            'action': {'type': 'text', 'payload': {'button': 'start'}, 'label': '☰ MENU'},
            'color': 'secondary'
        }]]
        keyboard = {'inline': True, 'buttons': button}
        kwargs.update(keyboard=json.dumps(keyboard, ensure_ascii=False))
    if repeat:
        kwargs.update(interval=repeat)
    coro = 'loop_send_message' if repeat else 'send_message'
    Task.objects.get_or_create(
        task_name=task_name,
        defaults={
            'coro': coro,
            'timers': [start_timer],
            'completed_timers': list(),
            'args': args,
            'kwargs': kwargs
        }
    )


def convert_template_to_message(template: str, convert_keys: dict) -> str:
    message = template
    for key, value in convert_keys.items():
        keys = ['{' + key + '}', '{ ' + key + '}', '{' + key + ' }', '{ ' + key + ' }']
        for real_key in keys:
            if real_key in message:
                message = message.replace(real_key, value)
                continue
    return message


def create_task_name(client: Client, message: ScheduledMessage):
    start_timer = int((message.scheduled_at - client.registered_at).total_seconds())
    task_name_prefix = {client.telegram_id: 'tg', client.vk_id: 'vk'}
    user_id = client.telegram_id or client.vk_id
    task_name = f'{task_name_prefix[user_id]}_{message.client_status}_{user_id}_{int(message.scheduled_at.timestamp())}'
    if message.repeat_interval:
        task_name += '_loop'
    return task_name, start_timer


def create_db_tasks_for_clients(clients: Union[QuerySet, set[Client]], message: ScheduledMessage):
    current_time = timezone.now() + timezone.timedelta(hours=5)
    if current_time > message.scheduled_at:
        return
    for client in clients:
        if isinstance(client, CourseClient):
            user = client.client
        else:
            user = client
        task_name, start_timer = create_task_name(user, message)
        create_db_task(
            user=client,
            task_name=task_name,
            message_template=message.message,
            start_timer=start_timer,
            repeat=message.repeat_interval
        )
