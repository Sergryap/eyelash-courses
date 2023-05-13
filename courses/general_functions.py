import pickle
import logging

from django.db.models import Window
from django.db.models.functions import DenseRank, Random
from django.conf import settings
from courses.models import CourseImage, Course
from django.utils import timezone
from django.core.mail import send_mail
from eyelash_courses.logger import send_message as send_tg_msg
from textwrap import dedent
from django.db.models import Q

logger = logging.getLogger('telegram')


def set_random_images(number):
    redis = settings.REDIS_DB
    random_images = CourseImage.objects.annotate(number=Window(expression=DenseRank(), order_by=[Random()]))
    end_index = min(len(random_images), number)
    part_random_images = random_images[:end_index]
    height = 80
    index_height = {(0, 4): 130, (5, 8): 100, (9, 13): 80, (14, 20): 60}
    for i, px in index_height.items():
        if i[0] <= end_index <= i[1]:
            height = px
            break
    io_random_images = pickle.dumps(part_random_images)
    redis.set('random_images', io_random_images)
    redis.set('height_images', height)
    return part_random_images, height


def get_courses(all_courses: Course, past=False, future=False):
    months = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    redis = settings.REDIS_DB
    if past and not future:
        courses = redis.get('past_courses')
        if courses:
            courses = pickle.loads(courses)
        else:
            courses = all_courses.filter(scheduled_at__lte=timezone.now())
            io_courses = pickle.dumps(courses)
            redis.set('past_courses', io_courses)
            redis.expire('past_courses', 1800)
    elif not past and future:
        courses = redis.get('future_courses')
        if courses:
            courses = pickle.loads(courses)
        else:
            courses = all_courses.filter(scheduled_at__gt=timezone.now())
            io_courses = pickle.dumps(courses)
            redis.set('future_courses', io_courses)
            redis.expire('future_courses', 1800)
    else:
        courses = all_courses

    return [
        {
            'instance': instance,
            'number': number,
            'image_url': instance.images.first().image.url,
            'image_preview_url': instance.images.first().image_preview.url,
            'big_preview_url': instance.images.first().big_preview.url,
            'date': instance.scheduled_at.strftime("%d.%m.%Y"),
            'date_slug': instance.scheduled_at.strftime("%d-%m-%Y"),
            'readable_date': {
                'day': instance.scheduled_at.day,
                'month': months[instance.scheduled_at.month],
                'year': instance.scheduled_at.year
            },
            'lecturer': instance.lecture.slug,
        } for number, instance in enumerate(courses, start=1)
    ]


def submit_course_form_data(name, phone, text):
    send_tg_msg(
        token=settings.TG_LOGGER_BOT,
        chat_id=settings.TG_LOGGER_CHAT,
        msg=dedent(text)
    )
    send_mail(
        f'Заявка от {name}: {phone}',
        dedent(text),
        settings.EMAIL_HOST_USER,
        settings.RECIPIENTS_EMAIL
    )


def get_error_data(form):
    error_msg = {
        'phone': 'Введите правильный номер',
        'email': 'Введите правильный email'
    }
    data = {field: msg for field, msg in error_msg.items() if field in form.errors}
    msg = '\n'.join([msg for msg in data.values()])
    return data, msg


def get_redis_or_get_db(key: str, obj_class):
    redis = settings.REDIS_DB
    io_items = redis.get(key)
    if io_items:
        items = pickle.loads(io_items)
        if items:
            return items
    items = obj_class.objects.all()
    io_items = pickle.dumps(items)
    redis.set(key, io_items)
    return items


def get_redis_or_get_db_all_courses(key: str):
    redis = settings.REDIS_DB
    all_courses = redis.get(key)
    if all_courses:
        all_courses = pickle.loads(all_courses)
    return all_courses or set_courses_redis()


def set_courses_redis():
    redis = settings.REDIS_DB
    all_courses = (
        Course.objects.filter(~Q(name='Фотогалерея'), published_in_bot=True)
        .select_related('program', 'lecture').prefetch_related('images')
    )
    io_all_courses = pickle.dumps(all_courses)
    settings.REDIS_DB.set('all_courses', io_all_courses)
    past_courses = all_courses.filter(scheduled_at__lte=timezone.now())
    future_courses = all_courses.filter(scheduled_at__gt=timezone.now())
    io_past_courses = pickle.dumps(past_courses)
    io_future_courses = pickle.dumps(future_courses)
    redis.set('past_courses', io_past_courses)
    redis.set('future_courses', io_future_courses)
    redis.expire('past_courses', 1800)
    redis.expire('future_courses', 1800)
    set_random_images(13)
    return all_courses
