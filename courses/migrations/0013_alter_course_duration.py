# Generated by Django 4.1.7 on 2023-03-05 06:12

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0012_course_description_alter_program_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='duration',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(limit_value=30)], verbose_name='Продолжительность курса'),
        ),
    ]