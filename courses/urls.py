from django.urls import path, re_path
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('courses/', views.course, name='course'),
    path('course/<slug:slug>/<slug:lecturer>/<slug:date>/', views.course_details, name='course_details'),
    path('program/<slug:slug>/', views.program_details, name='program_details'),
    path('faq/', views.faq, name='faq'),
    path('teacher-details/', views.teacher_details, name='teacher_details'),
]
