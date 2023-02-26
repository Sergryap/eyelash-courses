from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class Program(models.Model):
    title = models.CharField(
        verbose_name='Название программы',
        max_length=100,
        unique=True
    )
    description = models.TextField(
        verbose_name='Описание курса',
        blank=True,
        null=True,
    )

    def __str__(self):
        return f'{self.title}'

    class Meta:
        verbose_name = 'программа'
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
    description = models.TextField(
        verbose_name='Описание лектора',
        blank=True,
        null=True
    )

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


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
    telegram_id = models.PositiveIntegerField(
        verbose_name='Telegram Id',
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

    def __str__(self):
        return f'{self.first_name} {self.last_name}: {self.phone_number}'

    class Meta:
        verbose_name = 'клиент'
        verbose_name_plural = 'клиенты'


class Course(models.Model):
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
    duration = models.DurationField(
        verbose_name='Продолжительность курса',
        blank=True,
        null=True
    )
    name = models.CharField(
        verbose_name='Название курса',
        max_length=100,
    )
    price = models.PositiveIntegerField(
        verbose_name='Стоимость курса',
    )

    def __str__(self):
        return f'{self.program}: {self.scheduled_at.strftime("%d.%m.%Y")}'

    class Meta:
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'
        get_latest_by = 'scheduled_at'
        ordering = ['-scheduled_at']


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

    def __str__(self):
        return f'{self.course}: {self.client}'
