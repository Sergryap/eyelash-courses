# Generated by Django 4.1.7 on 2023-05-23 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0021_task_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='call_counter',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='счетчик'),
        ),
    ]
