import os
from django.core.management import BaseCommand
from courses.models import Course
from ._clean_course_images import clean_course_images


class Command(BaseCommand):
    help = 'Очистка директории с изображениями курсов от неиспользуемых файлов'

    def handle(self, *args, **options):
        clean_course_images()
