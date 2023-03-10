# Generated by Django 4.1.7 on 2023-02-27 17:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0008_alter_program_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, null=True, upload_to='courses')),
                ('position', models.IntegerField(default=0)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='courses.course')),
            ],
            options={
                'ordering': ['position'],
            },
        ),
    ]
