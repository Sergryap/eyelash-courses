import os
from django.core.management import BaseCommand
from courses.models import CourseImage
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from ._get_preview import get_preview


class Command(BaseCommand):
    help = 'Создание превью для галереи'

    def handle(self, *args, **options):
        courses = CourseImage.objects.all()
        for course in courses:
            get_preview(course)
            get_preview(course, attr='big_preview', width=370, height=320)
