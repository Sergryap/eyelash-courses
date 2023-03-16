import requests
from vk_bot.vk_lib import get_group_albums, get_album_photos
from django.conf import settings
from django.core.management import BaseCommand
from asgiref.sync import async_to_sync
from courses.models import Course, CourseImage
from django.utils import timezone
from django.core.files.base import ContentFile
from django.utils.crypto import md5


class Command(BaseCommand):
    help = 'Создание курсов из альбомов группы ВК'

    def handle(self, *args, **options):
        owner_id = '-' + str(settings.VK_GROUP_ID)
        exist_album_ids = [course.vk_album_id for course in Course.objects.all()]
        vk_albums = async_to_sync(get_group_albums)(owner_id)
        print(options.get('albums'))
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
            for photo in photos['response']['items']:
                photo_id = photo['id']
                photo_url = photo['sizes'][-1]['url']
                text = photo['text']
                response = requests.get(photo_url)
                response.raise_for_status()
                photo_instances.append(
                    CourseImage(
                        image_vk_id=f'photo{owner_id}_{photo_id}',
                        course=course,
                        image=ContentFile(response.content, name=md5(response.content).hexdigest())
                    )
                )
            CourseImage.objects.bulk_create(photo_instances)

