from asgiref.sync import sync_to_async
from vkwave.bots.utils.keyboards.keyboard import Keyboard, ButtonColor


BUTTONS_START = [
    ('Предстоящие курсы', 'future_courses'),
    ('Ваши курсы', 'client_courses'),
    ('Прошедшие курсы', 'past_courses'),
    ('Написать администратору', 'admin_msg'),
    ('Как нас найти', 'search_us')
]


async def get_course_msg(course_instances, back, successful_msg, not_successful_msg):
    count_courses = await course_instances.acount()
    keyboard = Keyboard(one_time=False, inline=True)
    if count_courses:
        msg = successful_msg
        for i, course in await sync_to_async(enumerate)(course_instances, start=1):
            keyboard.add_text_button(
                course.name,
                ButtonColor.PRIMARY,
                payload={'course_pk': course.pk, 'button': back}
            )
            keyboard.add_row()
        keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})
    else:
        msg = not_successful_msg
        keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})
    keyboard = keyboard.get_keyboard()

    return msg, keyboard


async def get_button_menu(inline=True):
    keyboard = Keyboard(one_time=False, inline=inline)
    buttons_color = ButtonColor.SECONDARY
    keyboard.add_text_button('☰ MENU', buttons_color, payload={'button': 'start'})

    return keyboard.get_keyboard()


async def get_button_course_menu(back, inline=True):
    keyboard = Keyboard(one_time=False, inline=inline)
    keyboard.add_text_button('НАЗАД', ButtonColor.PRIMARY, payload={'button': back})
    keyboard.add_row()
    keyboard.add_text_button('☰ MENU', ButtonColor.SECONDARY, payload={'button': 'start'})

    return keyboard.get_keyboard()
