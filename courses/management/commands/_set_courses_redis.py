import pickle
from courses.context_processors import set_random_images
from django.conf import settings
from django.utils import timezone
from courses.models import Course
from django.db.models import Q


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
