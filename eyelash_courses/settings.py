import dj_database_url
import redis
import logging

from pathlib import Path
from environs import Env
from .logger import MyLogsHandler


env = Env()
env.read_env()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

SECRET_KEY = env.str('SECRET_KEY')
DEBUG = env.bool('DEBUG', True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', ['127.0.0.1', 'localhost'])
VK_TOKEN = env.str('VK_TOKEN')
TG_TOKEN = env.str('TG_TOKEN')
VK_USER_TOKEN = env.str('VK_USER_TOKEN')
TG_LOGGER_BOT = env.str('TG_LOGGER_BOT')
TG_LOGGER_CHAT = env.str('TG_LOGGER_CHAT')
TG_BOT_NAME = env.str('TG_BOT_NAME')
YOUTUBE_CHANEL_ID = env.str('YOUTUBE_CHANEL_ID')
VK_GROUP_ID = env.int('VK_GROUP')
ADMIN_IDS = env.list('ADMIN_IDS')
TG_ADMIN_IDS = env.list('TG_ADMIN_IDS')
ADMIN_URL = env.str('ADMIN_URL')
SITE_HEADER = env.str('SITE_HEADER')
INDEX_TITLE = env.str('INDEX_TITLE')
SITE_TITLE = env.str('SITE_TITLE')
OFFICE_PHOTO = env.str('OFFICE_PHOTO')
SRC_MAP = env.str('SRC_MAP')
REDIS_DB = redis.Redis(
    host=env.str('REDIS_HOST'),
    port=env.str('REDIS_PORT'),
    password=env.str('REDIS_PASSWORD')
)

EMAIL_HOST = env.str('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT')
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
RECIPIENTS_EMAIL = env.list('RECIPIENTS_EMAIL')
EMAIL_HOST_PASSWORD = env.str('PASSWORD_EMAIL')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
SERVER_EMAIL = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
PHONE_NUMBER = env.str('PHONE_NUMBER')

logger = logging.getLogger('telegram')
logger.setLevel(logging.WARNING)
logger.addHandler(MyLogsHandler(TG_LOGGER_BOT, TG_LOGGER_CHAT))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'courses.apps.CoursesConfig',
    'adminsortable2',
    'tinymce',
    'import_export',
    'debug_toolbar',
    'django_async_orm'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware'
]

ROOT_URLCONF = 'eyelash_courses.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'courses.context_processors.get_footer_variables',
            ],
        },
    },
]

WSGI_APPLICATION = 'eyelash_courses.wsgi.application'


DATABASES = {'default': dj_database_url.config(env='DB_URL', conn_max_age=600)}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'ru-RU'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


INTERNAL_IPS = [
    '127.0.0.1'
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
