import json
from django.conf import settings


async def send_message(connect, chat_id, msg, *, reply_markup=None):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{connect['token']}/sendmessage"
    params = {
        'chat_id': chat_id,
        'text': msg,
        'reply_markup': reply_markup
    }
    for param, value in params.copy().items():
        if value is None:
            del params[param]
    async with connect['session'].get(url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())


async def send_location(connect, chat_id, *, lat, long, reply_markup=None):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{connect['token']}/sendlocation"
    params = {
        'chat_id': chat_id,
        'latitude': lat,
        'longitude': long,
        'reply_markup': reply_markup
    }
    for param, value in params.copy().items():
        if value is None:
            del params[param]
    async with connect['session'].get(url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())


async def send_photo(connect, chat_id, *, photo, caption=None, reply_markup=None):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{connect['token']}/sendphoto"
    params = {
        'chat_id': chat_id,
        'caption': caption,
        'reply_markup': reply_markup,
        'photo': photo
    }
    for param, value in params.copy().items():
        if value is None:
            del params[param]
    async with connect['session'].get(url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())