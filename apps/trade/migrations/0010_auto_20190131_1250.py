# Generated by Django 2.1.5 on 2019-01-31 12:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0009_auto_20190130_1436'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawmoney',
            name='time_rate',
            field=models.FloatField(blank=True, null=True, verbose_name='当时费率'),
        ),
        migrations.AlterField(
            model_name='orderinfo',
            name='pay_status',
            field=models.CharField(choices=[('NOTICE_FAIL', '通知失败'), ('TRADE_CLOSE', '支付关闭'), ('PAYING', '待支付'), ('TRADE_SUCCESS', '支付成功')], default='PAYING', max_length=30, verbose_name='订单状态'),
        ),
    ]