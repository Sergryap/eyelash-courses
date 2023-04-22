import os
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


def get_preview(
        obj,
        image_attr: str = 'image',
        preview_attr='image_preview',
        suffix: str = None,
        width=130, height=130
):

    """
    Создает превью изображения требуемого размера и записывает его в атрибут модели:

    obj - экземпляр модели;
    image_attr - атрибут модели, в котором находится исходное изображение;
    preview_attr - атрибут модели, в который будет записано превью, должно быть типа ImageField;
    suffix - для имени файла превью;
    width - максимальная ширина превью;
    height - максимальная ширина превью.
    """

    file_path = getattr(obj, image_attr).path
    suffix = suffix if suffix is not None else f'_{preview_attr}'
    new_filename_exclude_ext = f'{os.path.split(os.path.splitext(file_path)[0])[1]}{suffix}'
    new_filename = f'{new_filename_exclude_ext}.jpg'
    img = Image.open(file_path)
    remove_files = [file for file in os.listdir(os.path.split(file_path)[0]) if new_filename_exclude_ext in file]
    if hasattr(obj, preview_attr) and getattr(obj, preview_attr) and os.path.isfile(getattr(obj, preview_attr).path):
        for file in remove_files:
            print(f'Deleted: {file}')
            os.remove(os.path.join(os.path.split(file_path)[0], file))
    print(f'Created: {new_filename}')
    img.thumbnail((width, height))
    buffer = BytesIO()
    img.save(fp=buffer, format='JPEG')
    file_content = ContentFile(buffer.getvalue())
    preview = getattr(obj, preview_attr)
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
