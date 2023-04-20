import os
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


def get_preview(obj, attr='image_preview', width=130, height=130):
    file_path = obj.image.path
    new_filename = f'{os.path.split(os.path.splitext(file_path)[0])[1]}_{attr}.jpg'
    img = Image.open(file_path)
    img.thumbnail((width, height))
    buffer = BytesIO()
    img.save(fp=buffer, format='JPEG')
    file_content = ContentFile(buffer.getvalue())
    preview = getattr(obj, attr)
    preview.save(
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
