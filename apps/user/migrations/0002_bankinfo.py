# Generated by Django 2.1.5 on 2019-01-24 09:29

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='收款人')),
                ('account_num', models.CharField(max_length=35, verbose_name='账号')),
                ('bank_type', models.CharField(max_length=15, verbose_name='银行类型')),
                ('open_bank', models.CharField(blank=True, max_length=50, null=True, verbose_name='开户行')),
                ('add_time', models.DateTimeField(default=datetime.datetime.now, verbose_name='创建时间')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否激活')),
                ('last_time', models.DateTimeField(blank=True, null=True, verbose_name='最后收款时间')),
                ('total_money', models.FloatField(default=0.0, verbose_name='总收款')),
            ],
            options={
                'verbose_name': '支付宝管理',
                'verbose_name_plural': '支付宝管理',
            },
        ),
    ]