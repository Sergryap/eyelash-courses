# Generated by Django 4.1.7 on 2023-03-26 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_alter_client_telegram_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='program', verbose_name='Иллюстрация программы'),
        ),
    ]