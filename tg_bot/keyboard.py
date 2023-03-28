import json
from courses.models import CourseClient
from asgiref.sync import sync_to_async


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


async def get_course_buttons(course_instances, back):
    buttons = []
    for course in course_instances:
        if course.name == 'Фотогалерея':
            buttons.append(('ГАЛЕРЕЯ', f'c:{course.pk}:{back}'))
            continue
        buttons.append((course.name, f'c:{course.pk}:{back}'))
    return await get_callback_keyboard(buttons, column=2)


async def get_course_menu_buttons(back, course_pk, chat_id):
    course_clients = await CourseClient.objects.async_filter(course=course_pk)
    course_client_ids = [await sync_to_async(lambda: user.client.telegram_id)() for user in course_clients]
    buttons = []
    if back != 'client_courses' and back != 'past_courses' and chat_id not in course_client_ids:
        buttons.append(('ЗАПИСАТЬСЯ НА КУРС', f'en_{course_pk}_e'))
    elif chat_id in course_client_ids:
        buttons.append(('ОТМЕНИТЬ ЗАПИСЬ', f'en_{course_pk}_c'))
    buttons.extend([('НАЗАД', back)])
    return await get_callback_keyboard(buttons, column=2)


async def check_phone_button():

    return json.dumps(
        {
            'inline_keyboard': [
                [
                    {
                        'text': 'НОМЕР ВЕРНЫЙ',
                        'callback_data': 'phone_true'
                    },
                    {
                        'text': 'УКАЖУ ДРУГОЙ',
                        'callback_data': 'phone_false'
                    }
                ],
            ]
        }
    )
