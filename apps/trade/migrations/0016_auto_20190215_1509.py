# Generated by Django 2.1.5 on 2019-02-15 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0015_auto_20190215_1507'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='pay_status',
            field=models.CharField(choices=[('NOTICE_FAIL', '通知失败'), ('TRADE_SUCCESS', '支付成功'), ('PAYING', '待支付'), ('TRADE_CLOSE', '支付关闭')], default='PAYING', max_length=30, verbose_name='订单状态'),
        ),
    ]
