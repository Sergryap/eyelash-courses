# Generated by Django 4.1.7 on 2023-03-12 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0020_alter_course_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='short_description',
            field=models.TextField(blank=True, null=True, verbose_name='Сокращенное описание'),
        ),
    ]
