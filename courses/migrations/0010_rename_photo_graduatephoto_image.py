# Generated by Django 4.1.7 on 2023-04-13 06:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0009_graduatephoto'),
    ]

    operations = [
        migrations.RenameField(
            model_name='graduatephoto',
            old_name='photo',
            new_name='image',
        ),
    ]
