import os
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


def get_preview(obj, attr='image_preview', width=130, height=130):
    file_path = obj.image.path
    new_filename_exclude_ext = f'{os.path.split(os.path.splitext(file_path)[0])[1]}_{attr}'
    new_filename = f'{new_filename_exclude_ext}.jpg'
    img = Image.open(file_path)
    remove_files = [file for file in os.listdir(os.path.split(file_path)[0]) if new_filename_exclude_ext in file]
    if hasattr(obj, attr) and getattr(obj, attr) and os.path.isfile(getattr(obj, attr).path):
        for file in remove_files:
            print(f'Deleted: {file}')
            os.remove(os.path.join(os.path.split(file_path)[0], file))
    print(f'Created: {new_filename}')
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
