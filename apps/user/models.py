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
    is_proxy = models.BooleanField(default=False, verbose_name='是否代理')
    service_rate = models.FloatField(default=0.02, verbose_name='提现费率')
    level = models.IntegerField(default=3, verbose_name='用户等级')  # 1 超级用户 2 tuoxie 3 tuoxie001
    login_token = models.CharField(max_length=8, null=True, blank=True, verbose_name='副token')
    safe_code = models.CharField(max_length=32,default='e10adc3949ba59abbe56e057f20f883e',verbose_name='安全码')
    class Meta:
        verbose_name = '用户管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


class DeviceName(models.Model):
    user = models.ForeignKey(UserProfile, null=True, blank=True, related_name='devices', verbose_name='用户',
                             on_delete=models.CASCADE)
    username = models.CharField(max_length=25, null=True, blank=True, unique=True, verbose_name='设备名称')
    login_token = models.CharField(max_length=8, null=True, blank=True, verbose_name='token')
    auth_code = models.CharField(max_length=32, null=True, blank=True, verbose_name='用户验证码')
    add_time = models.DateTimeField(default=datetime.now, verbose_name='创建时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = '设备管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return str(self.id)


class BankInfo(models.Model):
    # 用户
    user = models.ForeignKey(UserProfile, null=True, blank=True, related_name='banks', verbose_name='用户',
                             on_delete=models.CASCADE)
    name = models.CharField(max_length=50, verbose_name='收款人')
    account_num = models.CharField(max_length=35, unique=True, verbose_name='账号')
    bank_type = models.CharField(max_length=15, verbose_name='银行类型')
    open_bank = models.CharField(max_length=50, null=True, blank=True, verbose_name='开户行')
    mobile = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    add_time = models.DateTimeField(default=datetime.now, verbose_name='创建时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    last_time = models.DateTimeField(null=True, blank=True, verbose_name='最后收款时间')
    total_money = models.FloatField(default=0.0, verbose_name='总收款')
    bank_tel = models.CharField(max_length=15, null=True, blank=True, verbose_name='银行电话')
    card_index = models.CharField(max_length=32, null=True, blank=True, verbose_name='卡索引')
    bank_mark = models.CharField(max_length=20, null=True, blank=True, verbose_name='银行编号')
    devices = models.ForeignKey(DeviceName, null=True, blank=True, related_name='banks', verbose_name='对应设备',
                                on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '收款管理'
        verbose_name_plural = verbose_name


class NoticeInfo(models.Model):
    title = models.CharField(max_length=100, verbose_name='公告标题')
    content = models.TextField(verbose_name='公告内容')
    add_time = models.DateTimeField(default=datetime.now, verbose_name='创建时间')

    class Meta:
        verbose_name = '公告管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class VersionInfo(models.Model):
    update_link = models.CharField(max_length=300, verbose_name='更新地址')
    version_no = models.CharField(max_length=100, verbose_name='版本号')
    remark = models.CharField(max_length=100, verbose_name='更新内容')
    add_time = models.DateTimeField(default=datetime.now, verbose_name='创建时间')

    class Meta:
        verbose_name = '版本管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.version_no
