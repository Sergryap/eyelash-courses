# Generated by Django 4.1.7 on 2023-04-20 13:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_courseimage_image_preview'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseimage',
            name='big_preview',
            field=models.ImageField(blank=True, null=True, upload_to='courses'),
        ),
    ]