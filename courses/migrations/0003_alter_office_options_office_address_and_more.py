# Generated by Django 4.1.7 on 2023-03-18 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_office'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='office',
            options={'verbose_name': 'офис', 'verbose_name_plural': 'офисы'},
        ),
        migrations.AddField(
            model_name='office',
            name='address',
            field=models.CharField(default='г.Пермь, ул. Тургенева, д. 23.', max_length=150, verbose_name='Адрес'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='office',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Описание'),
        ),
    ]
