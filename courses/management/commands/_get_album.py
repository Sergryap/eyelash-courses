import pickle
import time

import requests
from bots.vkvawe_bot.vk_lib import get_group_albums, get_album_photos
from django.conf import settings
from asgiref.sync import async_to_sync

from courses.management.commands._get_preview import get_preview
from courses.models import Course, CourseImage
from django.utils import timezone
from django.core.files.base import ContentFile
from django.utils.crypto import md5
from courses.context_processors import set_random_images
from django.db.models import Q


def get_albums(options: dict, albums_ids: str = None):
    owner_id = '-' + str(settings.VK_GROUP_ID)
    exist_album_ids = [course.vk_album_id for course in Course.objects.all()]
    vk_albums = async_to_sync(get_group_albums)(owner_id, albums_ids)
    for album in vk_albums['response']['items']:
        album_id = album['id']
        title = album['title']
        if album_id in exist_album_ids:
            print(f'Альбом: "{title}" уже существует и загружен')
            continue
        description = album['description']
        print(f'Загружаю альбом: "{title}"')
        course, _ = Course.objects.get_or_create(
            vk_album_id=album_id,
            defaults={
                'name': title,
                'scheduled_at': timezone.now(),
                'price': 0,
                'short_description': description
            }
        )
        photos = async_to_sync(get_album_photos)(owner_id, album_id)
        photo_instances = []
        i = 0
        for photo in photos['response']['items']:
            i += 1
            photo_id = photo['id']
            print(f'Загружаю фото: {photo_id}')
            photo_url = photo['sizes'][-1]['url']
            text = photo['text']
            response = requests.get(photo_url)
            response.raise_for_status()
            photo_instances.append(
                CourseImage(
                    image_vk_id=f'photo{owner_id}_{photo_id}',
                    course=course,
                    image=ContentFile(response.content, name=f'{md5(response.content).hexdigest()}.jpg')
                )
            )
            if i == 3:
                CourseImage.objects.bulk_create(photo_instances)
                photo_instances.clear()
                i = 0
                time.sleep(2)
        if i != 0:
            CourseImage.objects.bulk_create(photo_instances)
            photo_instances.clear()
            time.sleep(2)
        images = course.images.all()
        if images:
            for preview in images:
                print(f'Создаю превью фото: {preview.image.path}')
                get_preview(preview)
                get_preview(preview, preview_attr='big_preview', width=370, height=320)


def update_redis_courses():
    redis = settings.REDIS_DB
    all_courses = (
        Course.objects.filter(~Q(name='Фотогалерея'), published_in_bot=True)
        .select_related('program', 'lecture').prefetch_related('images')
    )
    io_all_courses = pickle.dumps(all_courses)
    settings.REDIS_DB.set('all_courses', io_all_courses)
    past_courses = all_courses.filter(scheduled_at__lte=timezone.now())
    future_courses = all_courses.filter(scheduled_at__gt=timezone.now())
    io_past_courses = pickle.dumps(past_courses)
    io_future_courses = pickle.dumps(future_courses)
    redis.set('past_courses', io_past_courses)
    redis.set('future_courses', io_future_courses)
    redis.expire('past_courses', 1800)
    redis.expire('future_courses', 1800)
    set_random_images(13)

