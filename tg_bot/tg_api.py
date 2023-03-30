import json
from django.conf import settings


async def send_message(connect, chat_id, msg, *, reply_markup=None, parse_mode=None):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{connect['token']}/sendmessage"
    params = {
        'chat_id': chat_id,
        'text': msg,
        'reply_markup': reply_markup,
        'parse_mode': parse_mode
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


async def send_photo(connect, chat_id, *, photo, caption=None, reply_markup=None,  parse_mode=None):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{connect['token']}/sendphoto"
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
    async with connect['session'].get(url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())


async def send_venue(connect, chat_id, *, lat, long, title, address, reply_markup=None):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{connect['token']}/sendvenue"
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
    async with connect['session'].get(url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())


async def send_media_group(connect, chat_id, *, media: list):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{connect['token']}/sendmediagroup"
    params = {
        'chat_id': chat_id,
        'media': json.dumps(media)
    }
    async with connect['session'].get(url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())


async def answer_callback_query(connect, *, callback_query_id: str, text: str):
    """Отправка уведомления ввиде всплывающего сообщения"""
    url = f"https://api.telegram.org/bot{connect['token']}/answercallbackquery"
    params = {
        'callback_query_id': callback_query_id,
        'text': text,
        'show_alert': 1
    }
    async with connect['session'].get(url, params=params) as res:
        res.raise_for_status()
        return json.loads(await res.text())
