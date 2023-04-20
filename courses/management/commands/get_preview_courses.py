import os
from django.core.management import BaseCommand
from courses.models import CourseImage
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


class Command(BaseCommand):
    help = 'Создание превью для галереи'

    def handle(self, *args, **options):
        courses = CourseImage.objects.all()
        for course in courses:
            file_path = course.image.path
            new_filename = f'{os.path.split(os.path.splitext(file_path)[0])[1]}_preview.jpg'
            img = Image.open(file_path)
            img.thumbnail((130, 130))
            buffer = BytesIO()
            img.save(fp=buffer, format='JPEG')
            file_content = ContentFile(buffer.getvalue())
            course.image_preview.save(
                new_filename,
                InMemoryUploadedFile(
                    file=file_content,
                    field_name=None,
                    name=new_filename,
                    content_type='image/jpeg',
                    size=file_content.tell,
                    charset=None
                )
            )
