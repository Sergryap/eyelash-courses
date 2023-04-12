from django.db.models import Window
from django.db.models.functions import DenseRank, Random

from courses.models import CourseImage


def get_random_images(request):
    random_images = CourseImage.objects.annotate(number=Window(expression=DenseRank(), order_by=[Random()]))
    end_index = min(len(random_images), 12)
    return {'random_images': random_images[:end_index]}
