from django.contrib import admin
from django import forms
from django.utils.html import format_html
from courses.models import Client, Course, Lecturer, Program, CourseClient, CourseImage
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline, SortableAdminBase
from django.db.models import Count, Value
from import_export import resources
from import_export.fields import Field
from import_export.admin import ExportMixin
from datetime import timedelta

admin.site.site_header = 'Курсы по наращиванию ресниц'   # default: "Django Administration"
admin.site.index_title = 'Управление сайтом'             # default: "Site administration"
admin.site.site_title = 'Курсы по наращиванию ресниц'    # default: "Django site admin"
admin.site.empty_value_display = '-empty-'


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
    fields = ['client']
    extra = 0


class CourseInline(admin.TabularInline):
    model = CourseClient
    fields = ['course']
    extra = 0


class CourseImageInline(SortableTabularInline, PreviewMixin):
    model = CourseImage
    fields = ['position', 'image', 'get_preview']
    readonly_fields = ['get_preview']
    extra = 3


class CourseProgramInline(admin.TabularInline):
    model = Course
    extra = 0


class ParticipantsCountFilter(admin.SimpleListFilter):
    title = 'Количество участников'
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
    list_display = ['title', 'description', 'get_preview']


class CourseForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['duration'].help_text = 'Длительность в днях'

    def clean(self):
        cleaned_data = super().clean()
        duration = cleaned_data['duration'].seconds
        day_duration = timedelta(days=int(duration))
        self.cleaned_data['duration'] = day_duration
        return self.cleaned_data


@admin.register(Course)
class CourseAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [CourseImageInline, ClientInline]
    list_display = ['__str__', 'program', 'price', 'lecture', 'get_count_participants', 'get_duration_days']
    list_editable = ['price']
    list_filter = ['scheduled_at', 'name', 'program', 'clients', ParticipantsCountFilter]
    save_on_top = True
    form = CourseForm


@admin.register(CourseImage)
class ImageAdmin(SortableAdminMixin, admin.ModelAdmin, PreviewMixin):
    list_display = ['id', 'get_preview', 'course', 'position']
    readonly_fields = ['get_preview']
    list_filter = ['course__program', 'course']


@admin.register(Client)
class ClientAdmin(ExportMixin, admin.ModelAdmin):
    inlines = [CourseInline]
    list_display = ['__str__', 'get_registry_date']
    list_filter = ['courses__program', 'courses', 'registered_at']
    resource_class = ClientResource


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    inlines = [CourseProgramInline]


@admin.register(CourseClient)
class CourseClientAdmin(admin.ModelAdmin):
    list_display = ['client', 'course', 'course_date']
    ordering = ['course', 'client']
    list_filter = ['course__program', 'course', 'client__registered_at']

    @admin.display(description='Дата курса')
    def course_date(self, obj):
        return obj.course.scheduled_at
