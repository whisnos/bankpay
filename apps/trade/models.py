from datetime import datetime

from django.db import models

# Create your models here.
from user.models import UserProfile


class OrderInfo(models.Model):
    PAY_STATUS = {
        ('PAYING', '待支付'),
        ('TRADE_SUCCESS', '支付成功'),
        ('TRADE_CLOSE', '支付关闭'),
        ('NOTICE_FAIL', '通知失败'),
    }
    user = models.ForeignKey(UserProfile, verbose_name='用户',on_delete=models.CASCADE)
    pay_status = models.CharField(default='PAYING', max_length=30, choices=PAY_STATUS, verbose_name='订单状态')
    total_amount = models.DecimalField(verbose_name='总金额',max_digits=7,decimal_places=2)
    order_no = models.CharField(max_length=100, unique=True, verbose_name='网站订单号')
    user_msg = models.CharField(max_length=200, null=True, blank=True, verbose_name='用户留言')
    pay_time = models.DateTimeField(null=True, blank=True, verbose_name="支付时间")
    add_time = models.DateTimeField(default=datetime.now, verbose_name='创建时间')
    order_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='商户订单号')
    bank_tel = models.CharField(max_length=15,null=True, blank=True, verbose_name='银行电话')
    account_num = models.CharField(max_length=32,null=True,blank=True,verbose_name='银行卡号')

    def __str__(self):
        return str(self.order_no)

    class Meta:
        verbose_name = '订单管理'
        verbose_name_plural = verbose_name

class WithDrawMoney(models.Model):
    user = models.ForeignKey(UserProfile, verbose_name='用户',on_delete=models.CASCADE)
    money = models.FloatField(verbose_name='提现金额')
    real_money = models.FloatField(null=True, blank=True, verbose_name='实际到账金额')
    # receive_way = models.CharField(max_length=20, choices=(('ALIPAY', '支付宝'), ('WECHAT', '微信'), ('BANK', '银行')),
    #                                verbose_name='提现类型')
    bank_type = models.CharField(max_length=15, null=True, blank=True, verbose_name='银行类型')
    add_time = models.DateTimeField(default=datetime.now, verbose_name='提现时间')
    withdraw_status = models.CharField(max_length=20,
                                       choices=(('0', '处理中'), ('1', '已处理')),
                                       default='0', verbose_name='提现状态')
    withdraw_no = models.CharField(max_length=50, unique=True, verbose_name='提现单号', null=True, blank=True)
    # 留言
    user_msg = models.CharField(max_length=200, null=True, blank=True, verbose_name='用户留言')
    receive_account = models.CharField(max_length=50, null=True, blank=True, verbose_name='账号')
    receive_time = models.DateTimeField(null=True, blank=True, verbose_name='到账时间')
    full_name = models.CharField(max_length=20, null=True, blank=True, verbose_name='姓名')
    # freeze_money = models.FloatField(default=0.0, verbose_name='冻结金额')
    # default_flag = models.BooleanField(default=False, verbose_name='旗帜')
    # time_rate = models.FloatField(null=True, blank=True, verbose_name='当时费率')
    open_bank = models.CharField(max_length=50, null=True, blank=True, verbose_name='开户行')
    receive_money_info = models.CharField(max_length=200, null=True, blank=True, verbose_name='收款信息')

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = '提现管理'
        verbose_name_plural = verbose_name