import json
import aiohttp
import redis


class TgApi:
    """Класс API методов Tg"""
    def __init__(self, tg_token: str, redis_db: redis.Redis, session: aiohttp.ClientSession = None):
        self.session = session
        self.token = tg_token
        self.redis_db = redis_db

    async def send_message(self, chat_id, msg, *, reply_markup=None, parse_mode=None):
        """Отправка сообщения через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendmessage"
        params = {
            'chat_id': chat_id,
            'text': msg,
            'reply_markup': reply_markup,
            'parse_mode': parse_mode
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def send_location(self, chat_id, *, lat, long, reply_markup=None):
        """Отправка локации через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendlocation"
        params = {
            'chat_id': chat_id,
            'latitude': lat,
            'longitude': long,
            'reply_markup': reply_markup
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def send_photo(self, chat_id, *, photo, caption=None, reply_markup=None, parse_mode=None):
        """Отправка фото через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendphoto"
        params = {
            'chat_id': chat_id,
            'caption': caption,
            'reply_markup': reply_markup,
            'photo': photo,
            'parse_mode': parse_mode
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def send_venue(self, chat_id, *, lat, long, title, address, reply_markup=None):
        """Отправка события через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendvenue"
        params = {
            'chat_id': chat_id,
            'latitude': lat,
            'longitude': long,
            'title': title,
            'address': address,
            'reply_markup': reply_markup
        }
        for param, value in params.copy().items():
            if value is None:
                del params[param]
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def send_media_group(self, chat_id, *, media: list):
        """Отправка нескольких медиа через api TG"""
        url = f"https://api.telegram.org/bot{self.token}/sendmediagroup"
        params = {
            'chat_id': chat_id,
            'media': json.dumps(media)
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def answer_callback_query(self, callback_query_id: str, text: str):
        """Отправка уведомления в виде всплывающего сообщения"""
        url = f"https://api.telegram.org/bot{self.token}/answercallbackquery"
        params = {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': 1
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def edit_message_reply_markup(self, chat_id, message_id, reply_markup):
        """Изменение существующей клавиатуры"""
        url = f"https://api.telegram.org/bot{self.token}/editmessagereplymarkup"
        params = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reply_markup': reply_markup
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())

    async def delete_message(self, chat_id, message_id):
        """Удаление существующей клавиатуры"""
        url = f"https://api.telegram.org/bot{self.token}/deletemessage"
        params = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        async with self.session.get(url, params=params) as res:
            res.raise_for_status()
            return json.loads(await res.text())


class TgEvent:
    def __init__(self, event):
        if event.get('message'):
            event_info = event['message']
            chat_event_info = event_info['chat']
            self.user_reply = event_info['text']
            self.chat_id = chat_event_info['id']
            self.first_name = chat_event_info['first_name']
            self.last_name = chat_event_info.get('last_name', '')
            self.username = chat_event_info.get('username', '')
            self.message_id = event_info['message_id']
            self.callback_query = False
            self.message = True

        elif event.get('callback_query'):
            event_info = event['callback_query']
            chat_event_info = event_info['message']['chat']
            self.user_reply = event_info['data']
            self.chat_id = chat_event_info['id']
            self.first_name = chat_event_info['first_name']
            self.last_name = chat_event_info.get('last_name', '')
            self.username = chat_event_info.get('username', '')
            self.callback_query_id = event_info['id']
            self.message_id = event_info['message']['message_id']
            self.callback_query = True
            self.message = False

        # elif
        # При необходимости добавить новые типы событий
        # return

        else:
            self.unknown_event = True
