# Generated by Django 2.1.5 on 2019-03-05 15:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0007_auto_20190227_1653'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='pay_status',
            field=models.CharField(choices=[('TRADE_SUCCESS', '支付成功'), ('TRADE_CLOSE', '支付关闭'), ('PAYING', '待支付'), ('NOTICE_FAIL', '通知失败')], default='PAYING', max_length=30, verbose_name='订单状态'),
        ),
    ]
