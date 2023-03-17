import logging
import requests
from time import sleep
logger = logging.getLogger('telegram')


def send_message(token, chat_id, msg: str):
    """Отправка сообщения через api TG"""
    url = f"https://api.telegram.org/bot{token}/sendmessage"
    payload = {'chat_id': chat_id, 'text': msg}
    while True:
        try:
            response = requests.get(url, params=payload)
            response.raise_for_status()
            return
        except (requests.exceptions.ReadTimeout, ConnectionError) as er:
            sleep(2)
            logger.warning(f'Ошибка на стороне Tg: {er}', stack_info=True)
            continue
        except Exception as err:
            logger.exception(err)


class MyLogsHandler(logging.Handler):

    def __init__(self, token, chat_id):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        send_message(token=self.token, chat_id=self.chat_id, msg=log_entry)