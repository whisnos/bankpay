# Generated by Django 2.1.5 on 2019-01-24 09:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_bankinfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankinfo',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='用户'),
        ),
    ]
