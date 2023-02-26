from django.contrib import admin
from courses.models import Client, Course, Lecturer, Program

admin.site.site_header = 'Курсы по наращиванию ресниц'   # default: "Django Administration"
admin.site.index_title = 'Управление сайтом'             # default: "Site administration"
admin.site.site_title = 'Курсы по наращиванию ресниц'    # default: "Django site admin"


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    pass


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    pass


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    pass


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    pass
