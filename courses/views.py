from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.conf import settings


def home(request):
    template = 'courses/index.html'
    return render(request, template)


def about(request):
    template = 'courses/about.html'
    return render(request, template)


def contact(request):
    template = 'courses/contact.html'
    return render(request, template)
