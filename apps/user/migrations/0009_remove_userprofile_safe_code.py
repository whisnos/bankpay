# Generated by Django 2.1.5 on 2019-03-05 16:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0008_auto_20190305_1559'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='safe_code',
        ),
    ]
