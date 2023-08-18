from __future__ import annotations

from typing import Union
from enum import Enum
from pydantic import BaseModel, Field, Json


class ServerParams(BaseModel):
    key: str
    server: str
    ts: str


class ServerResponse(BaseModel):
    response: ServerParams


class ReadState(Enum):
    NOT_RODE = 0
    RODE = 1


class Out(Enum):
    RECEIVED = 0
    SENT = 1


class Message(BaseModel):
    id: int | None = Field(
        default=None,
        description='Идентификатор сообщения (не возвращается для пересланных сообщений)'
    )
    user_id: int | None = Field(
        default=None,
        description='Идентификатор пользователя, в диалоге с которым находится сообщение.',
    )
    from_id: int | None = Field(
        default=None,
        description='Идентификатор автора сообщения. Положительное число.',
    )
    date: int | None = Field(
        default=None,
        description='Дата отправки сообщения в формате Unixtime'
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
    client_info: dict | None = None
    message: Message | None = None

    class Config:
        use_enum_values = True


class NewMessage(BaseModel):
    client_info: dict | None = None
    message: Message | None = None


class Update(BaseModel):
    type: str
    v: str
    event_id: str
    group_id: int
    object: Union[NewMessage, Message]


class ServerUpdates(BaseModel):
    ts: str
    updates: list[Update]
