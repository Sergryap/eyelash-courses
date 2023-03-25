import json


async def get_start_inline_keyboard():

    return json.dumps(
        {
            'inline_keyboard': [
                [
                    {
                        'text': '☰ MENU',
                        'callback_data': 'start'
                    },
                    {
                        'text': 'Предстоящие курсы',
                        'callback_data': 'future_courses'
                    }
                ],
            ]
        }
    )


async def get_start_keyboard():

    return json.dumps(
        {
            'keyboard': [
                [
                    {
                        'text': '☰ MENU',
                        'callback_data': 'start'
                    },
                    {
                        'text': 'Предстоящие курсы',
                        'callback_data': 'future_courses'
                    }
                ],
            ],
            'resize_keyboard': True
        }
    )


async def get_main_keyboard(column: int):
    start_buttons = [
        ('Предстоящие курсы', 'future_courses'),
        ('Прошедшие курсы', 'past_courses'),
        ('Ваши курсы', 'client_courses'),
        ('Как нас найти', 'search_us'),
        ('Галерея', 'gallery'),
        ('Написать администратору', 'admin_msg'),
    ]
    buttons, row = [], []
    i = 0
    for label, payload in start_buttons:
        i += 1
        row.append({'text': label, 'callback_data': payload})
        if i == column:
            buttons.append(row)
            row = []
            i = 0
    if i != 0:
        buttons.append(row)
    return json.dumps({'inline_keyboard': buttons})


async def get_callback_keyboard(buttons: list[tuple[str, str]], column: int, inline: bool = True):
    keyboard, row = [], []
    i = 0
    for label, payload in buttons:
        i += 1
        row.append({'text': label, 'callback_data': payload})
        if i == column:
            keyboard.append(row)
            row = []
            i = 0
    if i != 0:
        keyboard.append(row)
    if inline:
        return json.dumps({'inline_keyboard': keyboard})
    return json.dumps({'keyboard': keyboard, 'resize_keyboard': True})
