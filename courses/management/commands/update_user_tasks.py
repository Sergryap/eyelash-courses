from django.core.management import BaseCommand
from courses.models import Client, Task
from django.db.models import Q


class Command(BaseCommand):
    help = 'Очистка задач для пользователей'

    def handle(self, *args, **options):
        for user in Client.objects.all():
            for task in user.completed_tasks:
                if 'send_no_courses' in task:
                    user.completed_tasks.remove(task)
            user.save()
        Task.objects.filter(
            Q(task_name__istartswith='tg_send_no_courses') |
            Q(task_name__istartswith='vk_send_no_courses')
        ).delete()
