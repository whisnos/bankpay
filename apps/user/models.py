from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import datetime


# Create your models here.
class UserProfile(AbstractUser):
    mobile = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    name = models.CharField(max_length=25, null=True, blank=True, verbose_name='姓名')
    account_num = models.CharField(max_length=35, null=True, blank=True, verbose_name='收款账号')
    bank_type = models.CharField(max_length=15, null=True, blank=True, verbose_name='银行类型')
    open_bank = models.CharField(max_length=50, null=True, blank=True, verbose_name='开户行')
    uid = models.CharField(max_length=50, null=True, blank=True, verbose_name='用户uid')
    auth_code = models.CharField(max_length=32, null=True, blank=True, verbose_name='用户授权码')
    add_time = models.DateTimeField(default=datetime.now, verbose_name='注册时间')
    notify_url = models.CharField(max_length=100, null=True, blank=True, verbose_name='商户回调url')
    total_money = models.FloatField(default=0.0, verbose_name='当前收款余额')
    proxy = models.ForeignKey("self", null=True, blank=True, verbose_name="所属代理", help_text="所属代理",
                                 related_name="proxys", on_delete=models.CASCADE)
    is_proxy = models.BooleanField(default=False,verbose_name='是否代理')
    service_rate = models.FloatField(default=0.02, verbose_name='提现费率')
    level = models.IntegerField(default=3,verbose_name='用户等级') # 1 超级用户 2 tuoxie 3 tuoxie001
    login_token = models.CharField(max_length=8,null=True,blank=True,verbose_name='副token')
    class Meta:
        verbose_name = '用户管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


class BankInfo(models.Model):
    # 用户
    user = models.ForeignKey(UserProfile, null=True, blank=True, related_name='banks',verbose_name='用户', on_delete=models.CASCADE)
    name = models.CharField(max_length=50, verbose_name='收款人')
    account_num = models.CharField(max_length=35, verbose_name='账号')
    bank_type = models.CharField(max_length=15, verbose_name='银行类型')
    open_bank = models.CharField(max_length=50, null=True, blank=True, verbose_name='开户行')
    mobile = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    add_time = models.DateTimeField(default=datetime.now, verbose_name='创建时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    last_time = models.DateTimeField(null=True, blank=True, verbose_name='最后收款时间')
    total_money = models.FloatField(default=0.0, verbose_name='总收款')
    bank_tel = models.CharField(max_length=15,null=True, blank=True,verbose_name='银行电话')
    card_index = models.CharField(max_length=32,null=True,blank=True,verbose_name='卡索引')
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '收款管理'
        verbose_name_plural = verbose_name
