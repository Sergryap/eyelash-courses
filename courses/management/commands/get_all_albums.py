from django.core.management import BaseCommand
from ._get_album import get_albums, update_redis_courses


class Command(BaseCommand):
    help = 'Создание курсов из альбомов группы ВК'

    def handle(self, *args, **options):
        get_albums(options)
        update_redis_courses()

