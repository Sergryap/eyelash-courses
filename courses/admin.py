from django.contrib import admin
from courses.models import Client, Course, Lecturer, Program, CourseClient

admin.site.site_header = 'Курсы по наращиванию ресниц'   # default: "Django Administration"
admin.site.index_title = 'Управление сайтом'             # default: "Site administration"
admin.site.site_title = 'Курсы по наращиванию ресниц'    # default: "Django site admin"
admin.site.empty_value_display = '-empty-'


class ClientInline(admin.TabularInline):
    model = CourseClient
    fields = ['client']
    extra = 0


class CourseInline(admin.TabularInline):
    model = CourseClient
    fields = ['course']
    extra = 0


class CourseProgramInline(admin.TabularInline):
    model = Course
    extra = 0


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    inlines = [CourseProgramInline]
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
    inlines = [CourseProgramInline]


@admin.register(CourseClient)
class CourseClientAdmin(admin.ModelAdmin):
    list_display = ['client', 'course', 'course_date']
    ordering = ['course', 'client']

    @admin.display(description='Дата курса')
    def course_date(self, obj):
        return obj.course.scheduled_at
