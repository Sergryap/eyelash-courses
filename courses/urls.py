from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('courses/', views.course, name='course'),
    path('course/<slug:slug>/<slug:lecturer>/<slug:date>/', views.course_details, name='course_details'),
    path('program/<slug:slug>/', views.program_details, name='program_details'),
    path('teacher-details/', views.teacher_details, name='teacher_details'),
]
