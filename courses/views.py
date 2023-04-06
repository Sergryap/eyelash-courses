from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.conf import settings
from courses.models import Course, Program, Lecturer, Office
from django.db.models import Q
from django.utils import timezone
from datetime import datetime


def get_courses():
    return [
        {
            'instance': instance,
            'number': number,
            'image_url': instance.images.first().image.url,
            'date': instance.scheduled_at.strftime("%d.%m.%Y"),
            'date_slug': instance.scheduled_at.strftime("%d-%m-%Y"),
            'lecturer': instance.lecture.slug,
        } for number, instance in enumerate(
            Course.objects.filter(~Q(name='Фотогалерея'))
            .select_related('program', 'lecture')
            .prefetch_related('images'), start=10
        )
    ]


def home(request):
    template = 'courses/index.html'
    context = {
        'src_map': settings.SRC_MAP,
        'programs': Program.objects.all(),
        'courses': get_courses(),
        'office': Office.objects.first()
    }
    return render(request, template, context)


def about(request):
    template = 'courses/about.html'
    return render(request, template)


def contact(request):
    template = 'courses/contact.html'
    context = {'src_map': settings.SRC_MAP}
    return render(request, template, context)


def course(request):
    template = 'courses/course.html'
    context = {'courses': get_courses()}
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
    context = {
        'participants': max(course_instance.get_count_participants(), 2),
        'course': course_instance,
        'date': course_instance.scheduled_at.strftime("%d.%m.%Y"),
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
    courses = program.courses.prefetch_related('images')
    context = {
        'program': program,
        'courses': [
            {
                'instance': course_ins,
                'date': course_ins.scheduled_at.strftime("%d.%m.%Y"),
                'image_url': course_ins.images.first().image.url,
                'date_slug': course_ins.scheduled_at.strftime("%d-%m-%Y"),
                'lecturer': course_ins.lecture.slug,
            } for course_ins in courses if (
                    course_ins.scheduled_at > timezone.now()
                    and course_ins.published_in_bot
            )
        ]
    }
    return render(request, template, context)


def faq(request):
    template = 'courses/faq.html'
    return render(request, template)


def teacher_details(request):
    template = 'courses/teacher-details.html'
    return render(request, template)
