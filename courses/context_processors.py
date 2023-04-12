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


def get_footer_variables(request):
    random_images = CourseImage.objects.annotate(number=Window(expression=DenseRank(), order_by=[Random()]))
    end_index = min(len(random_images), 13)
    footer_form = False
    if request.method == 'POST' and request.POST['type_form'] == 'subscribe':
        footer_form = True
        subscribe_form = SubscribeForm(request.POST)
        if subscribe_form.is_valid():
            from_email = subscribe_form.cleaned_data['email']
            text = f'''
                Подписка на новости:
                Email: {from_email}
                '''
            try:
                send_mail(
                    f'Подписка на новости от {from_email}',
                    dedent(text),
                    settings.EMAIL_HOST_USER,
                    settings.RECIPIENTS_EMAIL
                )
                send_tg_msg(
                    token=settings.TG_LOGGER_BOT,
                    chat_id=settings.TG_LOGGER_CHAT,
                    msg=dedent(text)
                )
                messages.success(request, 'Отправлено!')
            except BadHeaderError:
                return HttpResponse('Ошибка в теме письма.')
        else:
            error_msg = {'email': 'Введите правильный email'}
            messages.error(request, error_msg)
            subscribe_form = SubscribeForm(error_msg)
    else:
        subscribe_form = SubscribeForm()

    return {
        'random_images': random_images[:end_index],
        'phone_number': settings.PHONE_NUMBER,
        'vk_group_id': settings.VK_GROUP_ID,
        'tg_bot_name': settings.TG_BOT_NAME,
        'youtube_chanel_id': settings.YOUTUBE_CHANEL_ID,
        'subscribe_form': subscribe_form,
        'footer_form': footer_form
    }
