# Generated by Django 4.1.7 on 2023-05-17 18:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0017_remove_course_reminder_intervals_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='timer',
            options={'ordering': ['reminder_interval'], 'verbose_name': 'Таймер', 'verbose_name_plural': 'Таймеры'},
        ),
        migrations.AlterField(
            model_name='course',
            name='reminder_intervals',
            field=models.ManyToManyField(related_name='courses', to='courses.timer', verbose_name='напомнить за'),
        ),
        migrations.AlterField(
            model_name='timer',
            name='reminder_interval',
            field=models.PositiveSmallIntegerField(default=18, verbose_name='Напомнить за'),
        ),
    ]