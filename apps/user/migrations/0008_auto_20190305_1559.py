# Generated by Django 2.1.5 on 2019-03-05 15:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_userprofile_safe_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='safe_code',
            field=models.CharField(default='e10adc3949ba59abbe56e057f20f883e', max_length=32, verbose_name='安全码'),
        ),
    ]
