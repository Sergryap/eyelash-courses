from __future__ import annotations

from typing import Union, Any
from enum import Enum
from pydantic import BaseModel, Field, Json


class ServerParams(BaseModel):
    key: str
    server: str
    ts: str
    act: str = 'a_check'
    wait: int = 25


class ServerResponse(BaseModel):
    response: ServerParams


class ReadState(Enum):
    NOT_RODE = 0
    RODE = 1


class Out(Enum):
    RECEIVED = 0
    SENT = 1


class Message(BaseModel):
    """This object represents a personal message.

    See here: https://dev.vk.com/ru/reference/objects/message
    """

    id: int | None = Field(
        description='Идентификатор сообщения (не возвращается для пересланных сообщений)'
    )
    user_id: int | None = Field(
        default=None,
        description='Идентификатор пользователя, в диалоге с которым находится сообщение.',
    )
    from_id: int | None = Field(
        description='Идентификатор автора сообщения. Положительное число.',
    )
    date: int | None = Field(
        description='Дата отправки сообщения в формате Unixtime',
        ge=1690000000,
    )
    conversation_message_id: int | None = Field(default=None, gt=0)
    read_state: ReadState | None = None
    ref: str | None = None
    ref_source: str | None = None
    out: Out | None = None
    title: str | None = None
    body: str | None = None
    text: str | None = None
    geo: dict | None = None
    attachments: list | None = None
    fwd_messages: list | None = None
    emoji: int | None = None
    important: bool | None = None
    deleted: bool | None = None
    is_hidden: bool | None = None
    payload: Json = Field(default={})
    peer_id: int | None = None
    random_id: int | None = None
    keyboard: dict | None = None
    reply_message: dict | None = None
    action: dict | None = None

    class Config:
        use_enum_values = True


class NewMessage(BaseModel):
    client_info: dict | None = None
    message: Message | None = None


class NewMessageUpdate(BaseModel):
    type: str
    v: str
    event_id: str
    group_id: int
    object: NewMessage


class ReplyMessageUpdate(BaseModel):
    type: str
    v: str
    event_id: str
    group_id: int
    object: Message


class Update(BaseModel):
    type: str
    v: str
    event_id: str
    group_id: int
    object: dict[str, Any]


class ServerUpdates(BaseModel):
    ts: str
    updates: list[Update]


class Fail(Enum):
    FAIL_1 = 1
    FAIL_2 = 2
    FAIL_3 = 3


class ServerFailedUpdate(BaseModel):
    failed: Fail
    ts: int | None = None

    class Config:
        use_enum_values = True


class GetLongPollServerParams(BaseModel):
    act: str = 'a_check'
    key: str | None = None
    ts: str | None = None
    wait: int = 25


class VkApiParams(BaseModel):
    access_token: str
    v: str = 5.131
    group_id: int | str

