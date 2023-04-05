from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.conf import settings
from courses.models import Course, Program, Lecturer
from django.db.models import Q


def home(request):
    template = 'courses/index.html'
    courses = [
        {
            'instance': instance,
            'image_url': instance.images.first().image.url,
            'date': instance.scheduled_at.strftime("%d.%m.%Y")
        } for instance in Course.objects.filter(~Q(name='Фотогалерея')).prefetch_related('images')
    ]

    context = {
        'src_map': settings.SRC_MAP,
        'programs': Program.objects.all(),
        'courses': courses
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
    context = {
        'courses': [
            {
                'instance': instance,
                'image_url': instance.images.first().image.url,
                'date': instance.scheduled_at.strftime("%d.%m.%Y"),
            } for instance in Course.objects.filter(~Q(name='Фотогалерея')).prefetch_related('images')
        ]
    }
    return render(request, template, context)


def course_details(request, slug: str):
    template = 'courses/course-details.html'
    course_instance = Course.objects.select_related('lecture').prefetch_related('images').get(slug=slug)
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
    context = {'program': Program.objects.get(slug=slug)}
    return render(request, template, context)


def faq(request):
    template = 'courses/faq.html'
    return render(request, template)


def teacher_details(request):
    template = 'courses/teacher-details.html'
    return render(request, template)
