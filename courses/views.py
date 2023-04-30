import pickle
import smtplib
from textwrap import dedent
from django.shortcuts import render, HttpResponse, get_object_or_404
from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from courses.forms import ContactForm, CourseForm
from django.contrib import messages
from courses.models import Course, Program, Office, GraduatePhoto
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from eyelash_courses.logger import send_message as send_tg_msg
from .context_processors import set_random_images
# from .tasks import send_message_task


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
        'programs': get_redis_or_get_db('programs', Program),
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
        'past_courses': get_courses(all_courses, past=True)
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
