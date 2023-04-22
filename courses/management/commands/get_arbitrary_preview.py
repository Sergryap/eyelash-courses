from django.core.management import BaseCommand
from courses.models import *
from ._get_preview import get_preview


class Command(BaseCommand):
    help = 'Создание превью для изображений модели'

    def add_arguments(self, parser):
        parser.add_argument('-m', '--model', required=True, type=str, help='Имя модели, содержащей изображения')
        parser.add_argument('-a', '--attribute', required=True, help='Поле модели для превью изображения')
        parser.add_argument('-wt', '--width', required=True, type=int, help='Ширина нового изображения, px')
        parser.add_argument('-ht', '--height', required=True, type=int, help='Высота нового изображения, px')

    def handle(self, *args, **options):
        model = globals()[options['model']]
        attribute = options['attribute']
        width = options['width']
        height = options['height']
        print(model, attribute, width, height)
        instances = model.objects.all()
        for instance in instances:
            get_preview(instance, preview_attr=attribute, width=width, height=height)
