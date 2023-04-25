import smtplib
import pickle

from django.db.models import Window
from django.db.models.functions import DenseRank, Random
from django.conf import settings
from courses.forms import SubscribeForm
from courses.models import CourseImage
from django.core.mail import send_mail, BadHeaderError
from django.contrib import messages
from django.shortcuts import HttpResponse
from eyelash_courses.logger import send_message as send_tg_msg
from textwrap import dedent
# from .tasks import send_message_task


def get_footer_variables(request):
    footer_form = False
    if request.method == 'POST' and request.POST.get('type_form', False) == 'subscribe':
        footer_form = True
        subscribe_form = SubscribeForm(request.POST)
        if subscribe_form.is_valid():
            from_email = subscribe_form.cleaned_data['email']
            text = f'''
                Подписка на новости:
                Email: {from_email.replace('@', '_собака_')}
                '''
            # send_message_task.delay(text=text)
            try:
                send_tg_msg(
                    token=settings.TG_LOGGER_BOT,
                    chat_id=settings.TG_LOGGER_CHAT,
                    msg=dedent(text)
                )
                messages.success(request, 'Отправлено!')
                send_mail(
                    f'Подписка на новости',
                    dedent(text),
                    settings.EMAIL_HOST_USER,
                    settings.RECIPIENTS_EMAIL
                )
            except BadHeaderError:
                return HttpResponse('Ошибка в теме письма.')
            except smtplib.SMTPDataError as err:
                send_tg_msg(
                    token=settings.TG_LOGGER_BOT,
                    chat_id=settings.TG_LOGGER_CHAT,
                    msg=str(err)
                )
        else:
            error_msg = {'email': 'Введите правильный email'}
            messages.error(request, error_msg)
            subscribe_form = SubscribeForm(error_msg)
    else:
        subscribe_form = SubscribeForm()

    redis = settings.REDIS_DB
    part_random_images = redis.get('random_images')
    height = redis.get('height_images')
    if part_random_images and height:
        part_random_images = pickle.loads(part_random_images)
        height = int(height)
    else:
        part_random_images, height = set_random_images(13)

    base_data = {
        'random_images': part_random_images,
        'phone_number': settings.PHONE_NUMBER,
        'phone_number_readable': settings.PHONE_NUMBER_READABLE,
        'vk_group_id': settings.VK_GROUP_ID,
        'tg_bot_name': settings.TG_BOT_NAME,
        'youtube_chanel_id': settings.YOUTUBE_CHANEL_ID,
        'subscribe_form': subscribe_form,
        'footer_form': footer_form,
        'height_picture': height
    }

    return base_data


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
