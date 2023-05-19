import aiohttp
import redis

from abc import ABC, abstractmethod


class AbstractAPI(ABC):

    @abstractmethod
    def __init__(self, redis_db: redis.Redis, session: aiohttp.ClientSession = None, loop=None):
        self.session = session
        self.redis_db = redis_db
        self.loop = loop
        self.sending_tasks = None

    @staticmethod
    @abstractmethod
    async def create_key_task(*args, **kwarg):
        pass

    @abstractmethod
    async def send_message(self, *args, **kwargs):
        pass

    @abstractmethod
    async def send_message_later(self, *args, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    async def create_reminder_text(*args, **kwargs):
        pass

    @abstractmethod
    async def create_message_sending_tasks(self, *args, **kwargs):
        pass

    @abstractmethod
    async def update_message_sending_tasks(self, *args, **kwargs):
        pass

    @abstractmethod
    async def delete_message_sending_tasks(self, *args, **kwargs):
        pass

    async def update_tasks_triggered_admin(self, key_trigger):
        """Обновление отложенных задач отправки, если были изменения в админ-панели"""

        if self.redis_db.get(key_trigger) and int(self.redis_db.get(key_trigger)):
            if self.sending_tasks:
                for __, task in self.sending_tasks.items():
                    task.cancel()
            self.sending_tasks = await self.update_message_sending_tasks()
            self.redis_db.delete(key_trigger)
