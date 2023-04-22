from django.core.management import BaseCommand
from ._compress_img import compress_img


class Command(BaseCommand):
    help = 'Изменение размера изображения'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--image_name', required=True, type=str, help='Файл изображения')
        parser.add_argument('-s', '--suffix', required=False, type=str,  help='Суффикс для нового имени файла')
        parser.add_argument('-wt', '--width', required=True, type=int, help='Максимальная ширина нового изображения, px')
        parser.add_argument('-ht', '--height', required=True, type=int, help='Максимальная высота нового изображения, px')
        parser.add_argument('-q', '--quality', required=False, type=int, help='Процент сжатия')

    def handle(self, *args, **options):
        compress_args = {}
        compress_args.update(image_name=options['image_name'])
        suffix = options.get('suffix')
        if suffix:
            compress_args.update(suffix=suffix)
        compress_args.update(width=options['width'])
        compress_args.update(height=options['height'])
        quality = options.get('quality')
        if quality:
            compress_args.update(quality=quality)
        print(compress_args)
        compress_img(**compress_args)



