# Generated by Django 4.1.7 on 2023-02-26 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_alter_course_options_rename_date_course_scheduled_at_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='client',
            options={'verbose_name': 'клиента', 'verbose_name_plural': 'клиенты'},
        ),
        migrations.AlterModelOptions(
            name='lecturer',
            options={'verbose_name': 'лектора', 'verbose_name_plural': 'лекторы'},
        ),
        migrations.AlterModelOptions(
            name='program',
            options={'verbose_name': 'программу', 'verbose_name_plural': 'программы'},
        ),
        migrations.AlterField(
            model_name='course',
            name='price',
            field=models.PositiveIntegerField(verbose_name='Стоимость, RUB'),
        ),
        migrations.AddConstraint(
            model_name='courseclient',
            constraint=models.UniqueConstraint(fields=('client', 'course'), name='unique_client_course'),
        ),
    ]
