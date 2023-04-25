import smtplib
from eyelash_courses import celery_app
from eyelash_courses.logger import send_message as send_tg_msg
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from textwrap import dedent
from asgiref.sync import async_to_sync
from vk_bot.vk_lib import (
    upload_photos_in_album,
    delete_photos,
    create_vk_album,
    edit_vk_album,
    make_main_album_photo
)
from courses.management.commands._get_preview import get_preview
from courses.models import Course, CourseImage
# celery -A eyelash_courses worker -c 3


@celery_app.task
def send_message_task(name=None, phone=None, text=None):
    """Отправка сообщений формы"""
    subject = f'Заявка от {name}: {phone}' if phone and name else 'Подписка на новости'
    try:
        send_tg_msg(
            token=settings.TG_LOGGER_BOT,
            chat_id=settings.TG_LOGGER_CHAT,
            msg=dedent(text)
        )
        send_mail(
            subject,
            dedent(text),
            settings.EMAIL_HOST_USER,
            settings.RECIPIENTS_EMAIL
        )
    except BadHeaderError as err:
        send_tg_msg(
            token=settings.TG_LOGGER_BOT,
            chat_id=settings.TG_LOGGER_CHAT,
            msg=str(f'{err}: Ошибка в теме письма.')
        )
    except smtplib.SMTPDataError as err:
        send_tg_msg(
            token=settings.TG_LOGGER_BOT,
            chat_id=settings.TG_LOGGER_CHAT,
            msg=str(err)
        )


@celery_app.task
def create_or_edit_vk_album(obj):
    if not obj.vk_album_id:
        album = async_to_sync(create_vk_album)(obj)
        obj.vk_album_id = album['response']['id']
        obj.save()
    else:
        async_to_sync(edit_vk_album)(obj)
    images = obj.images.all()
    if images:
        vk_album_id = obj.vk_album_id
        upload_photos = [image for image in images if not image.image_vk_id and image.upload_vk]
        if upload_photos:
            async_to_sync(upload_photos_in_album)(upload_photos, vk_album_id)


@celery_app.task
def upload_photos_in_album_task(upload_photos, vk_album_id):
    async_to_sync(upload_photos_in_album)(upload_photos, vk_album_id)


@celery_app.task
def course_admin_save_formset(instances):
    images = [image for image in instances if isinstance(image, CourseImage)]
    if images:
        for preview in images:
            get_preview(preview)
            get_preview(preview, preview_attr='big_preview', width=370, height=320)
        course_obj = images[0].course
        vk_album_id = course_obj.vk_album_id
        upload_photos = [image for image in images if not image.image_vk_id and image.upload_vk]
        if upload_photos:
            async_to_sync(upload_photos_in_album)(upload_photos, vk_album_id)

        # Установка главной фото альбома ВК
        course = list(Course.objects.filter(pk=course_obj.pk))
        if course:
            positions = [image.position for image in course[0].images.all()]
            min_positions = [position for position in positions if position == min(positions)]
        if course and len(min_positions) == 1:
            all_courses_images = list(course[0].images.all())
            main_image = sorted(all_courses_images, key=lambda image: image.position)[0]
        else:
            main_image = images[0]
        album_main_image_id = main_image.image_vk_id.split('_')[1]
        async_to_sync(make_main_album_photo)(vk_album_id, album_main_image_id)

    for image in images:
        if image.image_vk_id and not image.upload_vk:
            async_to_sync(delete_photos)(image)
            image.image_vk_id = None
            image.save()


@celery_app.task
def upgrade_courses_images(obj):
    images = obj.images.all()
    if images:
        for preview in images:
            get_preview(preview)
            get_preview(preview, preview_attr='big_preview', width=370, height=320)
        vk_album_id = obj.vk_album_id
        upload_photos = [image for image in images if not image.image_vk_id and image.upload_vk]
        if upload_photos:
            async_to_sync(upload_photos_in_album)(upload_photos, vk_album_id)


@celery_app.task
def upgrade_course_image(obj):
    get_preview(obj)
    get_preview(obj, preview_attr='big_preview', width=370, height=320)
    vk_album_id = obj.course.vk_album_id
    if not obj.image_vk_id and obj.upload_vk:
        async_to_sync(upload_photos_in_album)([obj], vk_album_id)
    if obj.image_vk_id and not obj.upload_vk:
        async_to_sync(delete_photos)(obj)
        obj.image_vk_id = None
        obj.save()
