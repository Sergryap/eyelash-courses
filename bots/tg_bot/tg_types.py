from __future__ import annotations

from enum import Enum
from typing import Any, Union, Optional

from pydantic import BaseModel, AnyHttpUrl, Field


class ParseMode(str, Enum):
    MarkdownV2 = 'MarkdownV2'  # https://core.telegram.org/bots/api#markdownv2-style
    HTML = 'HTML'  # https://core.telegram.org/bots/api#html-style
    Markdown = 'Markdown'  # legacy mode https://core.telegram.org/bots/api#markdown-style


class User(BaseModel):
    """This model represents a Telegram user or bot.

    See here: https://core.telegram.org/bots/api#user
    """

    id: int  # noqa A003
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    added_to_attachment_menu: bool | None = None
    can_join_groups: bool | None = None
    can_read_all_group_messages: bool | None = None
    supports_inline_queries: bool | None = None


class Chat(BaseModel):
    """This model represents a chat.

    See here: https://core.telegram.org/bots/api#chat
    """

    id: int  # noqa A003
    type: str  # noqa A003
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_forum: bool | None = None
    photo: dict[str, Any] | None = None
    active_usernames: list[str] | None = None
    emoji_status_custom_emoji_id: str | None = None
    bio: str | None = None
    has_private_forwards: bool | None = None
    has_restricted_voice_and_video_messages: bool | None = None
    join_to_send_messages: bool | None = None
    join_by_request: bool | None = None
    description: str | None = None
    invite_link: str | None = None
    pinned_message: Message | None = None
    permissions: dict[str, Any] | None = None
    slow_mode_delay: int | None = None
    message_auto_delete_time: int | None = None
    has_aggressive_anti_spam_enabled: bool | None = None
    has_hidden_members: bool | None = None
    has_protected_content: bool | None = None
    sticker_set_name: str | None = None
    can_set_sticker_set: bool | None = None
    linked_chat_id: int | None = None


class KeyboardButton(BaseModel):
    """This model represents one button of the reply keyboard.

    For simple text buttons, String can be used instead of this object to specify the button text.
    The optional fields web_app, request_user, request_chat, request_contact,
    request_location, and request_poll are mutually exclusive.

    See here: https://core.telegram.org/bots/api#keyboardbutton
    """

    text: str
    request_user: dict[str, Union[int, bool]] | None = None
    request_chat: dict[str, Union[int, bool, dict[str, bool]]] | None = None
    request_contact: bool | None = None
    request_location: bool | None = None
    request_poll: dict[str, str] | None = None
    web_app: dict[str, AnyHttpUrl] | None = None


class ReplyKeyboardMarkup(BaseModel):
    """This model represents a custom keyboard with reply options.

    See here: https://core.telegram.org/bots/api#replykeyboardmarkup
    """

    keyboard: list[list[KeyboardButton]]
    is_persistent: bool | None = None
    resize_keyboard: bool | None = None
    one_time_keyboard: bool | None = None
    input_field_placeholder: str | None = None
    selective: bool | None = None


class ReplyKeyboardRemove(BaseModel):
    """Upon receiving a message with this object, Telegram clients will remove the current.

    custom keyboard and display the default letter-keyboard. By default, custom keyboards
    are displayed until a new keyboard is sent by a bot. An exception is made for one-time
    keyboards that are hidden immediately after the user presses a button

    See here: https://core.telegram.org/bots/api#replykeyboardremove
    """

    remove_keyboard: bool
    selective: bool | None = None


class ForceReply(BaseModel):
    """Upon receiving a message with this object, Telegram clients will display a reply.

    interface to the user (act as if the user has selected the bot's message and tapped 'Reply').
    This can be extremely useful if you want to create user-friendly step-by-step interfaces
    without having to sacrifice privacy mode.

    See here: https://core.telegram.org/bots/api#forcereply
    """

    force_reply: bool
    input_field_placeholder: bool | None = None
    selective: bool | None = None


class InlineKeyboardButton(BaseModel):
    """This model represents one button of an inline keyboard.

    See here: https://core.telegram.org/bots/api#inlinekeyboardbutton
    """

    text: str
    url: str | None = None
    callback_data: str | None = None
    web_app: dict[str, AnyHttpUrl] | None = None
    login_url: dict[str, Union[str, bool]] | None = None
    switch_inline_query: str | None = None
    switch_inline_query_current_chat: str | None = None
    switch_inline_query_chosen_chat: dict[str, Union[str, bool]] | None = None
    callback_game: Any | None = None
    pay: bool | None = None


class InlineKeyboardMarkup(BaseModel):
    """This model represents an inline keyboard that appears right next to the message it belongs to.

    See here: https://core.telegram.org/bots/api#inlinekeyboardmarkup
    """

    inline_keyboard: list[list[InlineKeyboardButton]]


class Invoice(BaseModel):
    """This model contains basic information about an invoice.

    See here: https://core.telegram.org/bots/api#invoice
    """

    title: str
    description: str
    start_parameter: str
    currency: str
    total_amount: int


class ShippingAddress(BaseModel):
    """This object represents a shipping address.

    See here: https://core.telegram.org/bots/api#shippingaddress
    """

    country_code: str
    state: str
    city: str
    street_line1: str
    street_line2: str
    post_code: str


class OrderInfo(BaseModel):
    """This object represents information about an order.

    See here: https://core.telegram.org/bots/api#orderinfo
    """

    name: str | None = None
    phone_number: str | None = None
    email: str | None = None
    shipping_address: ShippingAddress | None = None


class SuccessfulPayment(BaseModel):
    """This object contains basic information about a successful payment.

    See here: https://core.telegram.org/bots/api#successfulpayment
    """

    currency: str
    total_amount: int
    invoice_payload: str
    shipping_option_id: str | None = None
    order_info: OrderInfo | None = None
    telegram_payment_charge_id: str | None = None
    provider_payment_charge_id: str | None = None


class MessageEntity(BaseModel):
    """This model represents one special entity in a text message.

    For example, hashtags, usernames, URLs, etc.

    See here: https://core.telegram.org/bots/api#messageentity
    """

    type: str  # noqa A003
    offset: int
    length: int
    url: str | None = None
    user: User | None = None
    language: str | None = None
    custom_emoji_id: str | None = None


class Message(BaseModel):
    """This model represents a message.

    See here: https://core.telegram.org/bots/api#message
    """

    message_id: int
    message_thread_id: int | None = None
    from_: User | None = Field(default=None, alias='from')
    sender_chat: Chat | None = None
    date: int
    chat: Chat
    forward_from: User | None = None
    forward_from_chat: Chat | None = None
    forward_from_message_id: int | None = None
    forward_signature: str | None = None
    forward_sender_name: str | None = None
    forward_date: int | None = None
    is_topic_message: dict[str, Any] | None = None
    is_automatic_forward: bool | None = None
    reply_to_message: Optional['Message'] = None
    via_bot: User | None = None
    edit_date: int | None = None
    has_protected_content: bool | None = None
    media_group_id: str | None = None
    author_signature: str | None = None
    text: str | None = None
    entities: list[MessageEntity] | None = None
    animation: dict[str, Any] | None = None
    audio: dict[str, Any] | None = None
    document: dict[str, Any] | None = None
    photo: list[dict[str, Any]] | None = None
    sticker: dict[str, Any] | None = None
    video: dict[str, Any] | None = None
    video_note: dict[str, Any] | None = None
    voice: dict[str, Any] | None = None
    caption: str | None = None
    caption_entities: list[MessageEntity] | None = None
    has_media_spoiler: bool | None = None
    contact: dict[str, Any] | None = None
    dice: dict[str, Any] | None = None
    game: dict[str, Any] | None = None
    poll: dict[str, Any] | None = None
    venue: dict[str, Any] | None = None
    location: dict[str, Any] | None = None
    new_chat_members: list[User] | None = None
    left_chat_member: User | None = None
    new_chat_title: str | None = None
    new_chat_photo: list[dict[str, Any]] | None = None
    delete_chat_photo: bool | None = None
    group_chat_created: bool | None = None
    supergroup_chat_created: bool | None = None
    channel_chat_created: bool | None = None
    message_auto_delete_timer_changed: list[dict[str, Any]] | None = None
    migrate_to_chat_id: int | None = None
    migrate_from_chat_id: int | None = None
    pinned_message: Optional['Message'] | None = None
    invoice: Invoice | None = None
    successful_payment: SuccessfulPayment | None = None
    user_shared: dict[str, Any] | None = None
    chat_shared: dict[str, Any] | None = None
    connected_website: str | None = None
    write_access_allowed: dict[str, Any] | None = None
    passport_data: dict[str, Any] | None = None
    proximity_alert_triggered: dict[str, Any] | None = None
    forum_topic_created: dict[str, Any] | None = None
    forum_topic_edited: dict[str, Any] | None = None
    forum_topic_closed: dict[str, Any] | None = None
    forum_topic_reopened: dict[str, Any] | None = None
    general_forum_topic_hidden: dict[str, Any] | None = None
    general_forum_topic_unhidden: dict[str, Any] | None = None
    video_chat_scheduled: dict[str, Any] | None = None
    video_chat_started: dict[str, Any] | None = None
    video_chat_ended: dict[str, Any] | None = None
    video_chat_participants_invited: dict[str, Any] | None = None
    web_app_data: dict[str, Any] | None = None
    reply_markup: InlineKeyboardMarkup | None = None


class MessageReplyMarkup(BaseModel):
    message_reply_markup: Union[Message, bool]


class InputMediaUrlPhoto(BaseModel):
    """This model represents a photo with url or file id.

    See here: https://core.telegram.org/bots/api#inputmediaphoto
    """

    type: str = 'photo' # noqa A003
    media: str
    caption: str | None = None
    parse_mode: str | None = None
    caption_entities: list[MessageEntity] | None = None
    has_spoiler: bool | None = None


class InputMediaBytesPhoto(BaseModel):
    """This model represents a photo with file.

    See here: https://core.telegram.org/bots/api#inputmediaphoto
    """

    type: str = 'photo' # noqa A003
    media: str
    media_content: bytes
    caption: str | None = None
    parse_mode: str | None = None
    caption_entities: list[MessageEntity] | None = None
    has_spoiler: bool | None = None


class InputMediaUrlDocument(BaseModel):
    """This model represents a document with url or file id.

    See here: https://core.telegram.org/bots/api#inputmediadocument
    """

    type: str = 'document' # noqa A003
    media: str
    thumbnail: str | None = None
    thumbnail_content: bytes | None = None
    caption: str | None = None
    parse_mode: str | None = None
    caption_entities: list[MessageEntity] | None = None
    disable_content_type_detection: bool | None = None


class InputMediaBytesDocument(BaseModel):
    """This model represents a document with file.

    See here: https://core.telegram.org/bots/api#inputmediadocument
    """

    type: str = 'document' # noqa A003
    media: str
    media_content: bytes
    thumbnail: str | None = None
    thumbnail_content: bytes | None = None
    caption: str | None = None
    parse_mode: str | None = None
    caption_entities: list[MessageEntity] | None = None
    disable_content_type_detection: bool | None = None


class CallbackQuery(BaseModel):
    data: str
    message: Message | None = Field(description='New incoming message of any kind - text, photo, sticker, etc.')
    from_: User | None = Field(default=None, alias='from')
    chat_instance: str | None = None


class Location(BaseModel):
    """This object represents a point on the map.

    See here: https://core.telegram.org/bots/api#location
    """

    longitude: float
    latitude: float
    horizontal_accuracy: float | None = None
    live_period: int | None = None
    heading: int | None = None
    proximity_alert_radius: int | None = None


class InlineQuery(BaseModel):
    """This object represents an incoming inline query.

    When the user sends an empty query, your bot could return some default or trending results.
    See here: https://core.telegram.org/bots/api#inlinequery
    """

    id: str # noqa A003
    from_: User = Field(alias='from')
    query: str
    offset: str
    chat_type: str | None = None
    location: Location | None = None


class ChosenInlineResult(BaseModel):
    """Represents a result of an inline query that was chosen by the user and sent to their chat partner.

    Note: It is necessary to enable inline feedback via @BotFather in order to receive these objects in updates.
    See here: https://core.telegram.org/bots/api#choseninlineresult
    """

    result_id: str
    from_: User = Field(alias='from')
    location: Location | None = None
    inline_message_id: str | None = None
    query: str | None = None


class ShippingQuery(BaseModel):
    """This object contains information about an incoming shipping query.

    See here: https://core.telegram.org/bots/api#shippingquery
    """

    id: str # noqa A003
    from_: User = Field(alias='from')
    invoice_payload: str # noqa A003
    shipping_address: ShippingAddress


class PreCheckoutQuery(BaseModel):
    """This object contains information about an incoming pre-checkout query.

    See here: https://core.telegram.org/bots/api#shippingquery
    """

    id: str # noqa A003
    from_: User = Field(alias='from')
    currency: str
    total_amount: int
    invoice_payload: str
    shipping_option_id: str | None = None
    order_info: OrderInfo | None = None


class PollOption(BaseModel):
    """This object contains information about one answer option in a poll.

    See here: https://core.telegram.org/bots/api#polloption
    """

    text: str
    voter_count: int


class Poll(BaseModel):
    """This object contains information about a poll.

    See here: https://core.telegram.org/bots/api#poll
    """

    id: str # noqa A003
    question: str
    options: list[PollOption]
    total_voter_count: int
    is_closed: bool
    is_anonymous: bool # noqa A003
    type: str # noqa A003
    allows_multiple_answers: bool
    correct_option_id: int | None = None # noqa A003
    explanation: str | None = None
    explanation_entities: list[MessageEntity] | None = None
    open_period: int | None = None
    close_date: int | None = None


class PollAnswer(BaseModel):
    """This object represents an answer of a user in a non-anonymous poll.

    See here: https://core.telegram.org/bots/api#pollanswer
    """

    poll_id: str
    user: User
    option_ids: list[int]


class ChatInviteLink(BaseModel):
    """Represents an invite link for a chat.

    See here: https://core.telegram.org/bots/api#chatinvitelink
    """

    invite_link: str
    creator: User
    creates_join_request: bool
    is_primary: bool
    is_revoked: bool
    name: str | None = None
    expire_date: int | None = None
    member_limit: int | None = None
    pending_join_request_count: int | None = None


class ChatJoinRequest(BaseModel):
    """Represents a join request sent to a chat.

    See here: https://core.telegram.org/bots/api#chatjoinrequest
    """

    chat: Chat
    from_: User = Field(alias='from')
    user_chat_id: int
    date: int
    bio: str | None = None
    invite_link: ChatInviteLink | None = None


class ChatMemberOwner(BaseModel):
    """Represents a join request sent to a chat.

    See here: https://core.telegram.org/bots/api#chatmemberowner
    """

    status: str
    user: User
    is_anonymous: bool
    custom_title: str


class ChatMemberAdministrator(BaseModel):
    """Represents a join request sent to a chat.

    See here: https://core.telegram.org/bots/api#chatmemberadministrator
    """

    status: str
    user: User
    can_be_edited: bool
    is_anonymous: bool
    can_manage_chat: bool
    can_delete_messages: bool
    can_manage_video_chats: bool
    can_restrict_members: bool
    can_promote_members: bool
    can_change_info: bool
    can_invite_users: bool
    can_post_messages: bool
    can_edit_messages: bool
    can_pin_messages: bool
    can_manage_topics: bool
    custom_title: bool


class ChatMemberMember(BaseModel):
    """Represents a join request sent to a chat.

    See here: https://core.telegram.org/bots/api#chatmembermember
    """

    status: str
    user: User


class ChatMemberRestricted(BaseModel):
    """Represents a join request sent to a chat.

    See here: https://core.telegram.org/bots/api#chatmemberrestricted
    """

    status: str
    user: User
    is_member: bool
    can_send_messages: bool
    can_send_audios: bool
    can_send_documents: bool
    can_send_photos: bool
    can_send_videos: bool
    can_send_video_notes: bool
    can_send_voice_notes: bool
    can_send_polls: bool
    can_send_other_messages: bool
    can_add_web_page_previews: bool
    can_change_info: bool
    can_invite_users: bool
    can_pin_messages: bool
    can_manage_topics: bool
    until_date: bool


class ChatMemberLeft(BaseModel):
    """Represents a join request sent to a chat.

    See here: https://core.telegram.org/bots/api#chatmemberleft
    """

    status: str
    user: User


class ChatMemberBanned(BaseModel):
    """Represents a join request sent to a chat.

    See here: https://core.telegram.org/bots/api#chatmemberbanned
    """

    status: str
    user: User
    until_date: int


class ChatMemberUpdated(BaseModel):
    """This object represents changes in the status of a chat member.

    See here: https://core.telegram.org/bots/api#chatmemberupdated
    """

    chat: Chat
    from_: User
    date: int
    old_chat_member: Union[
        ChatMemberOwner,
        ChatMemberAdministrator,
        ChatMemberMember,
        ChatMemberRestricted,
        ChatMemberLeft,
        ChatMemberBanned,
    ]
    new_chat_member: Union[
        ChatMemberOwner,
        ChatMemberAdministrator,
        ChatMemberMember,
        ChatMemberRestricted,
        ChatMemberLeft,
        ChatMemberBanned,
    ]
    invite_link: ChatInviteLink | None = None
    via_chat_folder_invite_link: bool


class Update(BaseModel):
    """This object represents an incoming update.

    See here: https://core.telegram.org/bots/api#update
    """

    update_id: int
    message: Message | None = Field(description='New incoming message of any kind - text, photo, sticker, etc.')
    edited_message: Message | None = Field(
        description='New version of a message that is known to the bot and was edited',
    )
    channel_post: Message | None = Field(
        description='New incoming channel post of any kind - text, photo, sticker, etc.',
    )
    edited_channel_post: Message | None = Field(
        description='New version of a channel post that is known to the bot and was edited',
    )
    inline_query: InlineQuery | None = None
    chosen_inline_result: ChosenInlineResult | None = None
    callback_query: CallbackQuery | None = None
    shipping_query: ShippingQuery | None = None
    pre_checkout_query: PreCheckoutQuery | None = None
    poll: Poll | None = None
    poll_answer: PollAnswer | None = None
    my_chat_member: ChatMemberUpdated | None = None
    chat_member: ChatMemberUpdated | None = None
    chat_join_request: ChatJoinRequest | None = None

    # TODO At most one of the optional parameters can be present in any given update.


class Response(BaseModel):
    ok: bool
    result: list[Update | None]


# fix ForwardRef fpr cyclic refernces Chat --> Message --> Chat
Chat.update_forward_refs()
