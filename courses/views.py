from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.conf import settings


def home(request):
    template = 'courses/index.html'
    context = {'src_map': settings.SRC_MAP}
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
    return render(request, template)


def course_details(request):
    template = 'courses/course-details.html'
    return render(request, template)


def faq(request):
    template = 'courses/faq.html'
    return render(request, template)


def teacher_details(request):
    template = 'courses/teacher-details.html'
    return render(request, template)
