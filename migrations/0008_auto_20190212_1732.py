# Generated by Django 2.1.5 on 2019-02-12 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('speech', '0007_auto_20190212_1731'),
    ]

    operations = [
        migrations.AlterField(
            model_name='audioclip',
            name='was_correct',
            field=models.BooleanField(),
        ),
    ]
