# Generated by Django 4.1.7 on 2023-04-30 06:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_courseimage_big_preview'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='program',
            options={'ordering': ['position'], 'verbose_name': 'программу', 'verbose_name_plural': 'программы'},
        ),
        migrations.AddField(
            model_name='program',
            name='position',
            field=models.IntegerField(default=0),
        ),
    ]
