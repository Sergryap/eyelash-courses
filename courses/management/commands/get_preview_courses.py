from django.core.management import BaseCommand
from courses.models import CourseImage
from ._get_preview import get_preview
from courses.views import set_courses_redis


class Command(BaseCommand):
    help = 'Создание превью для галереи'

    def handle(self, *args, **options):
        courses = CourseImage.objects.all()
        for course in courses:
            get_preview(course)
            get_preview(course, preview_attr='big_preview', width=370, height=320)
        set_courses_redis()
