# Generated by Django 4.1.7 on 2023-03-10 03:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0016_client_vk_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseimage',
            name='image_vk_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
