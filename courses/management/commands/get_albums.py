from django.core.management import BaseCommand
from ._get_album import get_albums


class Command(BaseCommand):
    help = 'Создание курсов из альбомов группы ВК с указанием конкретных альбомов'

    def add_arguments(self, parser):
        parser.add_argument('album_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        album_ids = ','.join([str(album_id) for album_id in options['album_ids']])
        get_albums(options, album_ids)
