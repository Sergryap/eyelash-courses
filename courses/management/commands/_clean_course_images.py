import os
from courses.models import Course


def clean_course_images():
    courses = Course.objects.prefetch_related('images')
    all_directory_files = {
        f'{os.getcwd()}/media/courses/{file}' for file in os.listdir(f'{os.getcwd()}/media/courses/')
    }
    print(f'Файлы в директории "/media/courses/":')
    for file in all_directory_files:
        print(file)
    course_files = {
        image_path.path
        for course in courses
        for image in course.images.all()
        for image_path in (image.image, image.image, image.image_preview)
    }
    for file in all_directory_files.difference(course_files):
        print(f'Удаление файла: {file}')
        os.remove(file)
