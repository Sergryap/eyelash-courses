# Generated by Django 4.1.7 on 2023-03-05 14:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0015_client_bot_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='vk_id',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Vk Id'),
        ),
    ]