from django.contrib import admin
from django.utils.safestring import mark_safe

from courses.models import Client, Course, Lecturer, Program, CourseClient

admin.site.site_header = 'Курсы по наращиванию ресниц'   # default: "Django Administration"
admin.site.index_title = 'Управление сайтом'             # default: "Site administration"
admin.site.site_title = 'Курсы по наращиванию ресниц'    # default: "Django site admin"
admin.site.empty_value_display = '-empty-'


class ClientInline(admin.TabularInline):
    model = CourseClient
    extra = 0


class CourseInline(admin.TabularInline):
    model = CourseClient
    extra = 0


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['title', 'description']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [ClientInline]
    list_display = ['__str__', 'price', 'lecture', 'get_count_participants', 'get_duration_days']
    list_editable = ['price']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    inlines = [CourseInline]
    list_display = ['__str__', 'get_registry_date']


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    pass
