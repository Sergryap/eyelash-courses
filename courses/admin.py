import random

from django.contrib import admin
from django import forms
from django.utils.html import format_html
from courses.models import Client, Course, Lecturer, Program, CourseClient, CourseImage
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline, SortableAdminBase
from django.db.models import Count, Value
from import_export import resources
from import_export.fields import Field
from import_export.admin import ExportMixin
from asgiref.sync import async_to_sync
from vk_bot.vk_lib import (
    upload_photos_in_album,
    delete_photos,
    create_vk_album,
    edit_vk_album,
    delete_album
)


admin.site.site_header = 'Курсы по наращиванию ресниц'   # default: "Django Administration"
admin.site.index_title = 'Управление сайтом'             # default: "Site administration"
admin.site.site_title = 'Курсы по наращиванию ресниц'    # default: "Django site admin"
admin.site.empty_value_display = 'Нет данных'


class PreviewMixin:
    @staticmethod
    @admin.display(description='Фото')
    def get_preview(obj):
        return format_html(
            '<img style="max-height:{height}" src="{url}"/>',
            height='200px',
            url=obj.image.url
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
    fields = ['position', 'image', 'get_preview', 'image_vk_id', 'upload_vk']
    readonly_fields = ['get_preview', 'image_vk_id']
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
class ProgramAdmin(admin.ModelAdmin, PreviewMixin):
    inlines = [CourseProgramInline]
    list_display = ['title', 'short_description', 'description', 'get_preview']
    readonly_fields = ['get_preview']


class CourseForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'duration' in self.fields:
            self.fields['duration'].help_text = 'Длительность в днях'


@admin.register(Course)
class CourseAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [CourseImageInline, ClientInline]
    list_display = [
        '__str__', 'program', 'price', 'lecture', 'get_course_preview', 'get_count_participants', 'duration'
    ]
    readonly_fields = ['get_course_preview']
    list_editable = ['price', 'program', 'duration']
    list_filter = ['scheduled_at', 'name', 'program', 'clients', ParticipantsCountFilter]
    save_on_top = True
    form = CourseForm
    fields = [
        ('name', 'program'),
        ('scheduled_at', 'price'),
        ('lecture', 'duration'),
        'short_description',
        'description'
    ]

    @admin.display(description='Фото из курса')
    def get_course_preview(self, obj):
        random_photo = random.choice(obj.images.all() or ['Фото не загружены'])
        if random_photo and isinstance(random_photo, CourseImage):
            return format_html(
                '<img style="max-height:{height}" src="{url}"/>',
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.vk_album_id:
            album = async_to_sync(create_vk_album)(obj)
            obj.vk_album_id = album['response']['id']
            obj.save()
        else:
            async_to_sync(edit_vk_album)(obj)
        images = obj.images.all()
        if images:
            vk_album_id = obj.vk_album_id
            upload_photos = get_upload_photos(images)
            if upload_photos:
                async_to_sync(upload_photos_in_album)(upload_photos, vk_album_id)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        async_to_sync(delete_album)(obj)

    def delete_queryset(self, request, queryset):
        for course in queryset:
            async_to_sync(delete_album)(course)
        queryset.delete()

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.deleted_objects:
            for deleted_image in formset.deleted_objects:
                if deleted_image.image_vk_id:
                    async_to_sync(delete_photos)(deleted_image)
        instances = formset.save(commit=False)
        images = [image for image in instances if isinstance(image, CourseImage)]
        if images:
            course_obj = images[0].course
            vk_album_id = course_obj.vk_album_id
            upload_photos = get_upload_photos(images)
            if upload_photos:
                async_to_sync(upload_photos_in_album)(upload_photos, vk_album_id)
        for image in images:
            if image.image_vk_id and not image.upload_vk:
                async_to_sync(delete_photos)(image)
                image.image_vk_id = None
                image.save()


def get_upload_photos(images):
    return [image for image in images if not image.image_vk_id and image.upload_vk]


@admin.register(CourseImage)
class ImageAdmin(SortableAdminMixin, admin.ModelAdmin, PreviewMixin):
    list_display = ['id', 'get_preview', 'course', 'image_vk_id', 'upload_vk', 'position']
    list_display_links = ['course']
    readonly_fields = ['get_preview', 'image_vk_id']
    list_filter = ['course__program', 'course']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        vk_album_id = obj.course.vk_album_id
        if not obj.image_vk_id and obj.upload_vk:
            async_to_sync(upload_photos_in_album)([obj], vk_album_id)
        if obj.image_vk_id and not obj.upload_vk:
            async_to_sync(delete_photos)(obj)
            obj.image_vk_id = None
            obj.save()


@admin.register(Client)
class ClientAdmin(ExportMixin, admin.ModelAdmin):
    inlines = [CourseInline]
    list_display = ['__str__', 'phone_number', 'telegram_id', 'get_vk_url', 'get_registry_date']
    list_filter = ['courses__program', 'courses', 'registered_at']
    readonly_fields = ['get_vk_url']
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


@admin.register(CourseClient)
class CourseClientAdmin(admin.ModelAdmin):
    list_display = ['client', 'course', 'course_date']
    ordering = ['course', 'client']
    list_filter = ['course__program', 'course', 'client__registered_at']

    @admin.display(description='Дата курса и время')
    def course_date(self, obj):
        return obj.course.scheduled_at
