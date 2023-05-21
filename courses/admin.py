import pickle
import random
import json

from django.conf import settings
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from courses.models import Client, Course, Lecturer, Program, CourseClient, CourseImage, Office, GraduatePhoto, Timer
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline, SortableAdminBase
from django.forms import CheckboxSelectMultiple
from django.db import models
from django.db.models import Count, Value
from import_export import resources
from import_export.fields import Field
from import_export.admin import ExportMixin
from bots import VkApi
from courses.management.commands._get_preview import get_preview
# from .tasks import course_admin_save_formset, upgrade_courses_images, upgrade_course_image


admin.site.site_header = settings.SITE_HEADER
admin.site.index_title = settings.INDEX_TITLE
admin.site.site_title = settings.SITE_TITLE
admin.site.empty_value_display = 'Нет данных'


class PreviewMixin:
    @staticmethod
    @admin.display(description='Фото')
    def get_image_preview(obj):
        url = (obj.big_preview.url if hasattr(obj, 'big_preview') else obj.image.url) or obj.image.url
        return format_html(
            '<img style="max-height:{height}" src="{url}">',
            height='200px',
            url=url
        )


class ClientResource(resources.ModelResource):
    first_name = Field(attribute='first_name', column_name='Имя')
    last_name = Field(attribute='last_name', column_name='Фамилия')
    phone_number = Field(attribute='phone_number', column_name='Телефон')
    registered_at = Field(attribute='registered_at', column_name='Регистрация')
    comment = Field(attribute='comment', column_name='Примечание')

    class Meta:
        model = Client
        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'telegram_id',
            'vk_profile',
            'registered_at',
            'comment'
        ]


class ClientInline(admin.TabularInline):

    model = CourseClient
    fields = ['client', 'get_client_phone', 'get_telegram_id', 'get_vk_profile']
    readonly_fields = ['get_client_phone', 'get_telegram_id', 'get_vk_profile']
    extra = 0

    @admin.display(description='Телефон клиента')
    def get_client_phone(self, obj):
        return obj.client.phone_number or 'Нет данных'

    @admin.display(description='Telegram Id')
    def get_telegram_id(self, obj):
        return obj.client.telegram_id or 'Нет данных'

    @admin.display(description='Профиль ВК')
    def get_vk_profile(self, obj):
        return obj.client.vk_profile or 'Нет данных'


class CourseInline(admin.TabularInline):
    model = CourseClient
    fields = ['course', 'get_lecture',  'get_data', 'get_course_price']
    readonly_fields = ['get_data',  'get_lecture', 'get_course_price']
    extra = 0

    @admin.display(description='Стоимость курса')
    def get_course_price(self, obj):
        return obj.course.price or 'Нет данных'

    @admin.display(description='Дата курса')
    def get_data(self, obj):
        return obj.course.scheduled_at.strftime("%d.%m.%Y") or 'Нет данных'

    @admin.display(description='Лектор')
    def get_lecture(self, obj):
        return obj.course.lecture or 'Нет данных'


class CourseImageInline(SortableTabularInline, PreviewMixin):
    model = CourseImage
    fields = ['position', 'image', 'get_image_preview', 'image_vk_id', 'upload_vk']
    readonly_fields = ['get_image_preview', 'image_vk_id']
    extra = 3


class CourseProgramInline(admin.TabularInline):
    model = Course
    fields = ['program', 'name', 'lecture', 'scheduled_at', 'price']
    readonly_fields = ['program', 'scheduled_at']
    extra = 0


class ParticipantsCountFilter(admin.SimpleListFilter):
    title = 'Участников'
    parameter_name = 'count_participants'

    def lookups(self, request, model_admin):
        return [
            ('0_3', 'До 3 чел.'),
            ('4_10', 'От 4 до 10 чел.'),
            ('11_100', 'Более 10 чел.')
        ]

    def queryset(self, request, queryset):

        if self.value() is not None:
            min_count, max_count = [int(value) for value in self.value().split('_')]
            return (
                queryset
                .annotate(count_participants=Count('clients'))
                .filter(
                    count_participants__gte=Value(min_count),
                    count_participants__lte=Value(max_count)
                )

            )


@admin.register(Program)
class ProgramAdmin(SortableAdminMixin, admin.ModelAdmin, PreviewMixin):
    inlines = [CourseProgramInline]
    prepopulated_fields = {'slug': ('title',)}
    list_display = ['title', 'get_image_preview', 'short_description', 'position']
    readonly_fields = ['get_image_preview']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        settings.REDIS_DB.set('programs', pickle.dumps(0))

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        settings.REDIS_DB.set('programs', pickle.dumps(0))

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        settings.REDIS_DB.set('programs', pickle.dumps(0))


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin, PreviewMixin):
    list_display = ['title', 'get_image_preview', 'address', 'long', 'lat']
    readonly_fields = ['get_image_preview']


class CourseForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'duration' in self.fields:
            self.fields['duration'].help_text = 'Длительность в днях'


@admin.register(Course)
class CourseAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [CourseImageInline, ClientInline]
    list_display = [
        '__str__', 'program', 'price', 'lecture', 'get_course_preview',
        'get_count_participants', 'duration', 'published_in_bot'
    ]
    readonly_fields = ['get_course_preview']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'program', 'duration', 'published_in_bot']
    list_filter = ['scheduled_at', 'name', 'program', 'clients', ParticipantsCountFilter]
    formfield_overrides = {
        models.ManyToManyField: {'widget': CheckboxSelectMultiple},
    }
    save_on_top = True
    form = CourseForm
    fields = [
        ('name', 'slug', 'program'),
        ('scheduled_at', 'price'),
        ('lecture', 'duration', 'reminder_intervals'),
        'short_description',
        'description'
    ]
    vk_api = VkApi(vk_user_token=settings.VK_USER_TOKEN, vk_group_id=settings.VK_GROUP_ID)

    @admin.display(description='Фото из курса')
    def get_course_preview(self, obj):
        random_photo = random.choice(obj.images.all() or ['Фото не загружены'])
        if random_photo and isinstance(random_photo, CourseImage):
            return format_html(
                '<img style="max-height:{height}" src="{url}">',
                height='150px',
                url=random_photo.image.url
            )
        return random_photo

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('program', 'lecture')
            .prefetch_related('clients', 'images')
        )

    @staticmethod
    def __update_bot_trigger_keys(redis, form, obj):
        if set(form.changed_data).intersection({'reminder_intervals', 'scheduled_at'}):
            if redis.get('update_vk_tasks') is None:
                print('update_vk_tasks')
                redis.set('update_vk_tasks', json.dumps([]))
            if redis.get('update_tg_tasks') is None:
                print('update_tg_tasks')
                redis.set('update_tg_tasks', json.dumps([]))
            update_vk_tasks = json.loads(redis.get('update_vk_tasks'))
            update_tg_tasks = json.loads(redis.get('update_tg_tasks'))
            update_vk_tasks.append(obj.pk)
            update_tg_tasks.append(obj.pk)
            redis.set('update_vk_tasks', json.dumps(update_vk_tasks))
            redis.set('update_tg_tasks', json.dumps(update_tg_tasks))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        redis = settings.REDIS_DB
        redis.set('all_courses', pickle.dumps(0))
        self.__update_bot_trigger_keys(redis, form, obj)
        if not obj.vk_album_id:
            album = self.vk_api.create_vk_album(obj)
            obj.vk_album_id = album['response']['id']
            obj.save()
        else:
            self.vk_api.edit_vk_album(obj)
        # upgrade_courses_images.delay(obj)
        images = obj.images.all()
        if images:
            for preview in images:
                get_preview(preview)
                get_preview(preview, preview_attr='big_preview', width=370, height=320)
            vk_album_id = obj.vk_album_id
            upload_photos = get_upload_photos(images)
            if upload_photos:
                self.vk_api.upload_photos_in_album(upload_photos, vk_album_id)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        settings.REDIS_DB.set('all_courses', pickle.dumps(0))

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        settings.REDIS_DB.set('all_courses', pickle.dumps(0))

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.deleted_objects:
            for deleted_object in formset.deleted_objects:
                if hasattr(deleted_object, 'image_vk_id') and deleted_object.image_vk_id:
                    self.vk_api.delete_photos(deleted_object)
        instances = formset.save(commit=False)
        # course_admin_save_formset.delay(instances)
        images = [image for image in instances if isinstance(image, CourseImage)]
        if images:
            for preview in images:
                get_preview(preview)
                get_preview(preview, preview_attr='big_preview', width=370, height=320)
            course_obj = images[0].course
            vk_album_id = course_obj.vk_album_id
            upload_photos = get_upload_photos(images)
            if upload_photos:
                self.vk_api.upload_photos_in_album(upload_photos, vk_album_id)

            # Установка главной фото альбома ВК
            course = list(Course.objects.filter(pk=course_obj.pk))
            if course:
                positions = [image.position for image in course[0].images.all()]
                min_positions = [position for position in positions if position == min(positions)]
            if course and len(min_positions) == 1:
                all_courses_images = list(course[0].images.all())
                main_image = sorted(all_courses_images, key=lambda image: image.position)[0]
            else:
                main_image = images[0]
            album_main_image_id = main_image.image_vk_id.split('_')[1]
            self.vk_api.make_main_album_photo(vk_album_id, album_main_image_id)

        for image in images:
            if image.image_vk_id and not image.upload_vk:
                self.vk_api.delete_photos(image)
                image.image_vk_id = None
                image.save()


def get_upload_photos(images):
    return [image for image in images if not image.image_vk_id and image.upload_vk]


@admin.register(CourseImage)
class ImageAdmin(SortableAdminMixin, admin.ModelAdmin, PreviewMixin):
    list_display = ['id', 'get_image_preview', 'course', 'image_vk_id', 'upload_vk', 'position']
    list_display_links = ['course']
    readonly_fields = ['get_image_preview', 'image_vk_id']
    list_filter = ['course__program', 'course']
    vk_api = VkApi(vk_user_token=settings.VK_USER_TOKEN, vk_group_id=settings.VK_GROUP_ID)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # upgrade_course_image.delay(obj)
        get_preview(obj)
        get_preview(obj, preview_attr='big_preview', width=370, height=320)
        vk_album_id = obj.course.vk_album_id

        if not obj.image_vk_id and obj.upload_vk:
            self.vk_api.upload_photos_in_album([obj], vk_album_id)
        if obj.image_vk_id and not obj.upload_vk:
            self.vk_api.delete_photos(obj)
            obj.image_vk_id = None
            obj.save()


@admin.register(Client)
class ClientAdmin(ExportMixin, admin.ModelAdmin):
    inlines = [CourseInline]
    list_display = ['__str__', 'phone_number', 'telegram_id', 'get_vk_url', 'get_registry_date']
    list_filter = ['courses__program', 'courses', 'registered_at']
    readonly_fields = ['get_vk_url', 'telegram_id']
    resource_class = ClientResource
    fields = [
        'first_name', 'last_name', 'phone_number',
        ('telegram_id', 'vk_profile'),
        'registered_at', 'comment'
    ]

    @staticmethod
    @admin.display(description='Страница VK')
    def get_vk_url(obj):
        if obj.vk_profile:
            return format_html(
                '<a href="{url}" target="_blank">{url}</a>',
                url=obj.vk_profile
            )
        return 'Нет данных'


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    inlines = [CourseProgramInline]
    prepopulated_fields = {'slug': ('first_name', 'last_name')}


@admin.register(CourseClient)
class CourseClientAdmin(admin.ModelAdmin):
    list_display = ['client', 'course', 'course_date']
    ordering = ['course', 'client']
    list_filter = ['course__program', 'course', 'client__registered_at']

    @admin.display(description='Дата курса и время')
    def course_date(self, obj):
        return obj.course.scheduled_at


@admin.register(GraduatePhoto)
class GraduatePhotoAdmin(admin.ModelAdmin, PreviewMixin):
    list_display = ['id', 'title', 'get_image_preview']
    readonly_fields = ['get_image_preview']
    list_editable = ['title']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        settings.REDIS_DB.set('graduate_photos', pickle.dumps(0))

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        settings.REDIS_DB.set('graduate_photos', pickle.dumps(0))

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        settings.REDIS_DB.set('graduate_photos', pickle.dumps(0))


@admin.register(Timer)
class TimerAdmin(admin.ModelAdmin):
    pass
