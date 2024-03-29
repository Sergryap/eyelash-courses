import json
from courses.models import CourseClient
from asgiref.sync import sync_to_async
from django.utils import timezone


async def get_start_buttons():
    start_buttons = [
        ('Предстоящие курсы', 'future_courses'),
        ('Ваши курсы', 'client_courses'),
        ('Прошедшие курсы', 'past_courses'),
        ('Написать администратору', 'admin_msg'),
        ('Как нас найти', 'search_us')
    ]
    buttons = []
    for label, payload in start_buttons:
        buttons.append(
            [
                {
                    'action': {'type': 'text', 'payload': {'button': payload}, 'label': label},
                    'color': 'secondary'
                }
            ],
        )
    keyboard = {'inline': True, 'buttons': buttons}
    return json.dumps(keyboard, ensure_ascii=False)


async def get_menu_button(color, inline):
    button = [
        [
            {
                'action': {'type': 'text', 'payload': {'button': 'start'}, 'label': '☰ MENU'},
                'color': color
            }
        ]
    ]
    keyboard = {'inline': inline, 'buttons': button}
    return json.dumps(keyboard, ensure_ascii=False)


async def get_course_buttons(course_instances, back):
    buttons = []
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    gallery_payload = None
    for course in course_instances:
        if course.name == 'Фотогалерея':
            gallery_payload = {'course_pk': course.pk, 'button': back}
            continue
        buttons.append(
            [
                {
                    'action': {
                        'type': 'text',
                        'payload': {'course_pk': course.pk, 'button': back},
                        'label': f'{course.name} - {course.scheduled_at.day} {months[course.scheduled_at.month]}'
                    },
                    'color': 'secondary'
                }
            ],
        )
    buttons.append(
        [
            {
                'action': {
                    'type': 'text',
                    'payload': {'button': 'start'},
                    'label': '☰ MENU'
                },
                'color': 'primary'
            }
        ],
    )
    if gallery_payload:
        buttons[-1].append(
            {
                'action': {
                    'type': 'text',
                    'payload': gallery_payload,
                    'label': 'ГАЛЕРЕЯ'
                },
                'color': 'primary'
            }
        )
    keyboard = {'inline': True, 'buttons': buttons}
    return json.dumps(keyboard, ensure_ascii=False)


async def check_phone_button():
    buttons = [
        [
            {
                'action': {
                    'type': 'text',
                    'payload': {'check_phone': 'true'},
                    'label': 'НОМЕР ВЕРНЫЙ'
                },
                'color': 'primary'
            }
        ],
        [
            {
                'action': {
                    'type': 'text',
                    'payload': {'check_phone': 'false'},
                    'label': 'УКАЖУ ДРУГОЙ'
                },
                'color': 'primary'
            }
        ],
        [
            {
                'action': {
                    'type': 'text',
                    'payload': {'button': 'start'},
                    'label': '☰ MENU'
                },
                'color': 'secondary'
            }
        ]
    ]
    keyboard = {'inline': True, 'buttons': buttons}
    return json.dumps(keyboard, ensure_ascii=False)


async def get_course_menu_buttons(back, course, user_id):
    course_clients = await CourseClient.objects.async_filter(course=course)
    course_client_ids = [await sync_to_async(lambda: user.client.vk_id)() for user in course_clients]
    buttons = []
    if back != 'client_courses' and back != 'past_courses' and user_id not in course_client_ids:
        buttons.append(
            [
                {
                    'action': {
                        'type': 'text',
                        'payload': {'entry': course.pk},
                        'label': 'ЗАПИСАТЬСЯ НА КУРС'
                    },
                    'color': 'secondary'
                }
            ]
        )

    elif user_id in course_client_ids and course.scheduled_at > timezone.now():
        buttons.append(
            [
                {
                    'action': {
                        'type': 'text',
                        'payload': {'entry': course.pk, 'cancel': 1},
                        'label': 'ОТМЕНИТЬ ЗАПИСЬ'
                    },
                    'color': 'secondary'
                }
            ]
        )
    buttons.append(
        [
            {
                'action': {
                    'type': 'text',
                    'payload': {'button': back},
                    'label': 'НАЗАД'
                },
                'color': 'secondary'
            },
            {
                'action': {
                    'type': 'text',
                    'payload': {'button': 'start'},
                    'label': '☰ MENU'
                },
                'color': 'primary'
            }
        ]
    )
    keyboard = {'inline': True, 'buttons': buttons}
    return json.dumps(keyboard, ensure_ascii=False)
