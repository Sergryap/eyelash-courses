import json
import aiohttp
import requests
import redis
import random

from more_itertools import chunked


class VkApi:
    """Класс API методов Vk"""
    def __init__(
            self,
            vk_group_token: str = None,
            vk_user_token: str = None,
            vk_group_id: int = None,
            redis_db: redis.Redis = None,
            session: aiohttp.ClientSession = None
    ):
        self.session = session
        self.token = vk_group_token
        self.user_token = vk_user_token
        self.vk_group_id = vk_group_id
        self.redis_db = redis_db

    async def send_message(
            self,
            user_id: int,
            message: str,
            user_ids: str = None,
            keyboard: str = None,
            attachment: str = None,
            payload: str = None,
            sticker_id: int = None,
            lat: str = None,
            long: str = None,
    ):
        send_message_url = 'https://api.vk.com/method/messages.send'
        params = {
            'access_token': self.token, 'v': '5.131',
            'user_id': user_id,
            'user_ids': user_ids,
            'random_id': random.randint(0, 1000),
            'message': message,
            'attachment': attachment,
            'keyboard': keyboard,
            'payload': payload,
            'sticker_id': sticker_id,
            'lat': lat,
            'long': long
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.post(send_message_url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def get_user(self, user_ids: str):
        get_users_url = 'https://api.vk.com/method/users.get'
        params = {
            'access_token': self.token,
            'v': '5.131',
            'user_ids': user_ids
        }
        async with self.session.get(get_users_url, params=params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
            return response.get('response')

    def upload_photos_in_album(self, photo_instances, vk_album_id, /):
        """Загрузка фотографий в альбом группы ВК"""

        upload_server_url = 'https://api.vk.com/method/photos.getUploadServer'
        photos_save_url = 'https://api.vk.com/method/photos.save'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'album_id': vk_album_id,
            'group_id': self.vk_group_id
        }

        for photo_sequence_part in chunked(photo_instances, 5):
            upload_response = requests.get(url=upload_server_url, params=params)
            upload_response.raise_for_status()
            upload = upload_response.json()
            upload_url = upload['response']['upload_url']
            upload_photos = {}
            photo_order = []
            for i, photo in enumerate(photo_sequence_part, start=1):
                photo_order.append(photo)
                upload_photos.update({f'file{i}': open(photo.image.path, 'rb')})
            photo_response = requests.post(url=upload_url, files=upload_photos)
            saving_photos = photo_response.json()
            for closed_file in upload_photos.values():
                closed_file.close()

            res = requests.post(
                url=photos_save_url,
                params={
                    **params,
                    'server': saving_photos['server'],
                    'photos_list': saving_photos['photos_list'],
                    'hash': saving_photos['hash'],
                }
            )
            res.raise_for_status()
            photos = res.json()

            if photos.get('response'):
                for photo, photo_instance in zip(photos['response'], photo_order):
                    attachment = f'photo{photo["owner_id"]}_{photo["id"]}'
                    photo_instance.image_vk_id = attachment
                    photo_instance.save()

    def delete_photos(self, obj, /):
        """Удаление одной фотографии из альбома группы ВК"""

        delete_photos_url = 'https://api.vk.com/method/photos.delete'
        photo_id = obj.image_vk_id.split('_')[1]
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'owner_id': f"-{self.vk_group_id}",
            'photo_id': photo_id
        }
        res = requests.post(url=delete_photos_url, params=params)
        res.raise_for_status()

    def create_vk_album(self, obj, /):
        """Создание пустого альбома vk"""
        create_vk_album_url = 'https://api.vk.com/method/photos.createAlbum'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'title': obj.name,
            'group_id': self.vk_group_id,
            'description': obj.short_description,
            'upload_by_admins_only': 1,
        }
        response = requests.post(url=create_vk_album_url, params=params)
        response.raise_for_status()
        return response.json()

    def edit_vk_album(self, obj, /):
        """Редактирование существующего альбома VK"""

        edit_vk_album_url = 'https://api.vk.com/method/photos.editAlbum'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'album_id': str(obj.vk_album_id),
            'owner_id': '-' + str(self.vk_group_id),
            'title': obj.name,
            'description': obj.short_description,
            'upload_by_admins_only': 1,
        }
        res = requests.post(url=edit_vk_album_url, params=params)
        res.raise_for_status()

    def make_main_album_photo(self, vk_album_id, photo_id, /):
        """Назначение обложки альбома VK"""

        photos_makeсover_url = 'https://api.vk.com/method/photos.makeCover'
        params = {
            'access_token': self.user_token,
            'v': '5.131',
            'owner_id': '-' + str(self.vk_group_id),
            'photo_id': photo_id,
            'album_id': str(vk_album_id),
        }
        res = requests.post(url=photos_makeсover_url, params=params)
        res.raise_for_status()
