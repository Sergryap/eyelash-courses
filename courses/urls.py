from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('courses/', views.course, name='course'),
    path('course-details/', views.course_details, name='course_details'),
    path('faq/', views.faq, name='faq'),
]
