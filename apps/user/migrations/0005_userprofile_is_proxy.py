# Generated by Django 2.1.5 on 2019-01-24 09:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_auto_20190124_1754'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_proxy',
            field=models.BooleanField(default=False, verbose_name='是否代理'),
        ),
    ]
