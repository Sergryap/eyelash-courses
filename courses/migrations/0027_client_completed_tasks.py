# Generated by Django 4.1.7 on 2023-05-28 16:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0026_alter_task_args_alter_task_completed_timers_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='completed_tasks',
            field=models.JSONField(blank=True, default=list, null=True, verbose_name='Выполненные задачи'),
        ),
    ]