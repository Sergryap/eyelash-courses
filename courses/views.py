import smtplib
import random
from django.shortcuts import render, HttpResponse, get_object_or_404
from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from courses.forms import ContactForm, CourseForm
from django.contrib import messages
from courses.models import Course, Program, Office, GraduatePhoto
from django.utils import timezone
from datetime import datetime
from eyelash_courses.logger import send_message as send_tg_msg
from .general_functions import (
    get_courses,
    submit_course_form_data,
    get_error_data,
    get_redis_or_get_db_all_courses,
    get_redis_or_get_db
)

# from .tasks import send_message_task


def home(request):
    template = 'courses/index.html'
    if request.method == 'POST' and request.POST['type_form'] == 'registration':
        form = ContactForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data['message']
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            from_email = form.cleaned_data['email']
            desire_date = form.cleaned_data['date']
            desire_course = form.cleaned_data['course']
            text = f'''
                Заявка на обучение:
                Имя: {name}
                Email: {from_email.replace('@', '_собака_')}
                Тел.: {phone}
                Желаемая дата: {desire_date}
                Курс: {desire_course}    
                Сообщение: {message}           
                '''
            # send_message_task.delay(name, phone, text)
            # messages.success(request, 'Отправлено!')
            try:
                submit_course_form_data(name, phone, text)
                messages.success(request, 'Отправлено!')
            except BadHeaderError:
                return HttpResponse('Ошибка в теме письма.')
            except smtplib.SMTPDataError as err:
                send_tg_msg(
                    token=settings.TG_LOGGER_BOT,
                    chat_id=settings.TG_LOGGER_CHAT,
                    msg=str(err)
                )
        else:
            data, msg = get_error_data(form)
            messages.error(request, msg)
            form = ContactForm(form.cleaned_data | data)
    else:
        form = ContactForm()

    all_courses = get_redis_or_get_db_all_courses('all_courses')
    context = {
        'src_map': settings.SRC_MAP,
        'courses': get_courses(all_courses, future=True),
        'past_courses': get_courses(all_courses, past=True),
        'office': get_redis_or_get_db('office', Office).first(),
        'graduate_photos': get_redis_or_get_db('graduate_photos', GraduatePhoto),
        'form': form
    }
    return render(request, template, context)


def course(request):
    template = 'courses/course.html'
    all_courses = get_redis_or_get_db_all_courses('all_courses')
    context = {
        'future_courses': get_courses(all_courses, future=True),
        'past_courses': get_courses(all_courses, past=True),
        'banner': random.choice(settings.BANNER_IMAGES),
    }
    return render(request, template, context)


def course_details(request, slug: str, lecturer: str, date: str):
    template = 'courses/course-details.html'
    scheduled_at = datetime.strptime(date, '%d-%m-%Y')
    course_instance = (
        Course.objects
        .filter(scheduled_at__date=scheduled_at, slug=slug, lecture__slug=lecturer)
        .select_related('lecture')
        .prefetch_related('images')[0]
    )
    if request.method == 'POST' and request.POST['type_form'] == 'registration':
        form = CourseForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            from_email = form.cleaned_data['email']
            text = f'''
                Заявка на курс:
                Имя: {name}
                Email: {from_email.replace('@', '_собака_')}
                Тел.: {phone}
                Курс: {course_instance.name}             
                '''
            # send_message_task.delay(name, phone, text)
            # messages.success(request, 'Отправлено!')
            try:
                submit_course_form_data(name, phone, text)
                messages.success(request, 'Отправлено!')
            except BadHeaderError:
                return HttpResponse('Ошибка в теме письма.')
            except smtplib.SMTPDataError as err:
                send_tg_msg(
                    token=settings.TG_LOGGER_BOT,
                    chat_id=settings.TG_LOGGER_CHAT,
                    msg=str(err)
                )
        else:
            data, msg = get_error_data(form)
            messages.error(request, msg)
            form = CourseForm(form.cleaned_data | data)
    else:
        form = CourseForm()
    context = {
        'form': form,
        'banner': random.choice(settings.BANNER_IMAGES),
        'participants': max(course_instance.get_count_participants(), 2),
        'course': course_instance,
        'date': course_instance.scheduled_at.strftime("%d.%m.%Y"),
        'start_time': course_instance.scheduled_at.strftime("%H:%M"),
        'images': [
            {
                'url': image.image.url, 'number': number
            } for number, image in enumerate(course_instance.images.all(), start=1)
        ]
    }
    return render(request, template, context)


def program_details(request, slug: str):
    template = 'courses/program-details.html'
    program = Program.objects.prefetch_related('courses').get(slug=slug)
    courses = program.courses.select_related('lecture').prefetch_related('images')

    if request.method == 'POST' and request.POST['type_form'] == 'registration':
        form = CourseForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            from_email = form.cleaned_data['email']
            text = f'''
                Заявка на индивидуальную программу:
                Имя: {name}
                Email: {from_email.replace('@', '_собака_')}
                Тел.: {phone}
                программа: {program.title}             
                '''
            # send_message_task.delay(name, phone, text)
            # messages.success(request, 'Отправлено!')
            try:
                submit_course_form_data(name, phone, text)
                messages.success(request, 'Отправлено!')
            except BadHeaderError:
                return HttpResponse('Ошибка в теме письма.')
            except smtplib.SMTPDataError as err:
                send_tg_msg(
                    token=settings.TG_LOGGER_BOT,
                    chat_id=settings.TG_LOGGER_CHAT,
                    msg=str(err)
                )
        else:
            data, msg = get_error_data(form)
            messages.error(request, msg)
            form = CourseForm(form.cleaned_data | data)
    else:
        form = CourseForm()

    context = {
        'form': form,
        'program': program,
        'banner': random.choice(settings.BANNER_IMAGES),
        'courses': [
            {
                'instance': course_ins,
                'date': course_ins.scheduled_at.strftime("%d.%m.%Y"),
                'image_url': course_ins.images.first().image.url,
                'image_preview_url': course_ins.images.first().image_preview.url,
                'date_slug': course_ins.scheduled_at.strftime("%d-%m-%Y"),
                'lecturer': course_ins.lecture.slug,
            } for course_ins in courses if (
                    course_ins.scheduled_at > timezone.now()
                    and course_ins.published_in_bot
            )
        ]
    }

    return render(request, template, context)


def teacher_details(request):
    template = 'courses/teacher-details.html'
    return render(request, template)

