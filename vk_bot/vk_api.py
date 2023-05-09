import json
import aiohttp
import redis
import random


class VkApi:
    """Класс API методов Vk"""
    def __init__(self, vk_group_token: str, redis_db: redis.Redis, session: aiohttp.ClientSession = None):
        self.session = session
        self.token = vk_group_token
        self.redis_db = redis_db

    async def get_long_poll_server(self, group_id: int):
        get_album_photos_url = 'https://api.vk.com/method/groups.getLongPollServer'
        params = {'access_token': self.token, 'v': '5.131', 'group_id': group_id}
        async with self.session.get(get_album_photos_url, params=params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
            key = response['response']['key']
            server = response['response']['server']
            ts = response['response']['ts']
            return key, server, ts

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
            'access_token': self.token, 'v': '5.131',
            'user_ids': user_ids
        }
        async with self.session.get(get_users_url, params=params) as res:
            res.raise_for_status()
            response = json.loads(await res.text())
            return response.get('response')
