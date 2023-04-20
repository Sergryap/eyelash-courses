from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib import admin
from tinymce.models import HTMLField
from django.core.validators import MaxValueValidator, MinValueValidator


class Office(models.Model):
    title = models.CharField(
        verbose_name='Название офиса',
        max_length=150,
    )
    address = models.CharField(
        verbose_name='Адрес',
        max_length=150,
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True,
        null=True,
    )
    image = models.ImageField(
        verbose_name='Фото офиса',
        upload_to='office'
    )
    long = models.DecimalField(
        max_digits=17,
        decimal_places=14,
        validators=[
            MinValueValidator(limit_value=-180),
            MaxValueValidator(limit_value=180)
        ]
    )
    lat = models.DecimalField(
        max_digits=16,
        decimal_places=14,
        validators=[
            MinValueValidator(limit_value=-90),
            MaxValueValidator(limit_value=90)
        ]
    )

    def __str__(self):
        return f'{self.title}'

    class Meta:
        verbose_name = 'офис'
        verbose_name_plural = 'офисы'


class Program(models.Model):
    title = models.CharField(
        verbose_name='Название программы',
        max_length=100,
        unique=True
    )
    description = HTMLField(
        verbose_name='Описание программы',
        blank=True,
        null=True,
    )
    short_description = models.TextField(
        verbose_name='Сокращенное описание',
        blank=True,
        null=True,
    )
    image = models.ImageField(
        verbose_name='Иллюстрация программы',
        upload_to='program',
        blank=True,
        null=True,
    )
    slug = models.SlugField(null=True)

    def __str__(self):
        return f'{self.title}'

    class Meta:
        verbose_name = 'программу'
        verbose_name_plural = 'программы'


class Lecturer(models.Model):
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=50
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=50
    )
    description = HTMLField(
        verbose_name='Описание лектора',
        blank=True,
        null=True
    )
    slug = models.SlugField(null=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'лектора'
        verbose_name_plural = 'лекторы'


class Client(models.Model):
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=50
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=50,
        blank=True,
        null=True
    )
    phone_number = PhoneNumberField(
        verbose_name='Телефон',
        region='RU',
        null=True,
        blank=True
    )
    telegram_id = models.PositiveBigIntegerField(
        verbose_name='Telegram Id',
        null=True,
        blank=True
    )
    vk_id = models.PositiveIntegerField(
        verbose_name='Vk Id',
        null=True,
        blank=True
    )
    vk_profile = models.URLField(
        verbose_name='Профиль ВК',
        null=True,
        blank=True
    )
    registered_at = models.DateTimeField(
        verbose_name='Время регистрации',
        default=timezone.now
    )
    comment = models.TextField(
        verbose_name='Заметки о клиенте',
        blank=True,
        null=True
    )
    bot_state = models.CharField(
        'Текущее состояние бота',
        max_length=50,
        help_text="Стейт-машина бота",
        default='START'
    )

    @admin.display(description='Дата регистрации')
    def get_registry_date(self):
        return self.registered_at.strftime("%d.%m.%Y")

    def __str__(self):
        return f'{self.first_name} {self.last_name}'#: {self.phone_number}'

    class Meta:
        verbose_name = 'клиента'
        verbose_name_plural = 'клиенты'


class Course(models.Model):
    name = models.CharField(
        verbose_name='Название курса',
        max_length=100,
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        related_name='courses',
        verbose_name='программа',
        null=True
    )
    lecture = models.ForeignKey(
        Lecturer,
        on_delete=models.SET_NULL,
        related_name='courses',
        verbose_name='лектор',
        null=True
    )
    clients = models.ManyToManyField(
        Client,
        verbose_name='Клиенты',
        related_name='courses',
        through='CourseClient'
    )
    scheduled_at = models.DateTimeField(
        verbose_name='Дата и время курса',
    )
    duration = models.PositiveSmallIntegerField(
        verbose_name='Дней',
        validators=[MaxValueValidator(limit_value=30)],
        blank=True,
        null=True
    )
    price = models.PositiveIntegerField(
        verbose_name='Стоимость, RUB',
    )
    description = HTMLField(
        verbose_name='Описание курса',
        blank=True,
        null=True,
    )
    short_description = models.TextField(
        verbose_name='Сокращенное описание',
        blank=True,
        null=True,
    )
    vk_album_id = models.PositiveIntegerField(
        verbose_name='Идентификатор альбома ВК для курса',
        blank=True,
        null=True
    )
    published_in_bot = models.BooleanField(
        verbose_name='В боте',
        default=True
    )
    slug = models.SlugField(null=True)

    @admin.display(description='Участников')
    def get_count_participants(self):
        return self.clients.count()

    def __str__(self):
        return f'{self.name}: {self.scheduled_at.strftime("%d.%m.%Y")}, {self.duration} дней'

    class Meta:
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'
        get_latest_by = 'scheduled_at'
        ordering = ['scheduled_at']


class GraduatePhoto(models.Model):
    image = models.ImageField(upload_to='graduate_photos')
    title = models.CharField(
        verbose_name='Выпуск',
        max_length=100,
        blank=True,
        null=True
    )


class CourseImage(models.Model):
    image = models.ImageField(
        upload_to='courses',
        blank=True,
        null=True
    )
    image_preview = models.ImageField(
        upload_to='courses',
        blank=True,
        null=True
    )
    big_preview = models.ImageField(
        upload_to='courses',
        blank=True,
        null=True
    )
    image_vk_id = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Курс'
    )
    upload_vk = models.BooleanField(
        verbose_name='Загрузить в ВК',
        default=True
    )
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ['position']
        verbose_name = 'Фото'
        verbose_name_plural = 'Фото к курсу'

    def __str__(self):
        return f'{self.course}'


class CourseClient(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='клиент'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='курс'
    )
    feedback = models.TextField(
        verbose_name='Отзыв клиента',
        blank=True,
        null=True
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['client', 'course'],
                name='unique_client_course',
            )
        ]
        verbose_name = 'Курс - клиент'
        verbose_name_plural = 'Курсы по клиентам'

    def __str__(self):
        return f'{self.course}: {self.client.first_name} {self.client.last_name}'
