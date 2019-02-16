import datetime
import time

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_jwt.utils import jwt_decode_handler
import re

from trade.models import OrderInfo
from user.models import UserProfile, BankInfo
from django.db.models import Q, Sum

from utils.make_code import make_uuid_code, make_auth_code, make_login_token


class RegisterUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(label='用户名', required=True, min_length=5, max_length=20, allow_blank=False,
                                     validators=[
                                         UniqueValidator(queryset=UserProfile.objects.all(), message='用户名不能重复')
                                     ], help_text='用户名')
    password = serializers.CharField(label='密码', write_only=True, required=True, allow_blank=False, min_length=6,
                                     style={'input_type': 'password'}, help_text='密码')
    password2 = serializers.CharField(label='确认密码', write_only=True, required=True, allow_blank=False, min_length=6,
                                      style={'input_type': 'password'}, help_text='重复密码')
    mobile = serializers.CharField(label='手机号', required=True, allow_blank=False, min_length=11, max_length=11,
                                   validators=[
                                       UniqueValidator(queryset=UserProfile.objects.all(), message='手机号不能重复')
                                   ], help_text='手机号')
    uid = serializers.CharField(label='uid', read_only=True, validators=[
        UniqueValidator(queryset=UserProfile.objects.all(), message='uid不能重复')
    ], help_text='用户uid')
    auth_code = serializers.CharField(label='授权码', read_only=True, validators=[
        UniqueValidator(queryset=UserProfile.objects.all(), message='授权码不能重复')
    ], help_text='用户授权码')

    class Meta:
        model = UserProfile
        fields = ['username', 'password', 'password2', 'mobile', 'uid', 'auth_code']

    def validate_mobile(self, data):
        if not re.match(r'^1([38][0-9]|4[579]|5[0-3,5-9]|6[6]|7[0135678]|9[89])\d{8}$', data):
            raise serializers.ValidationError('手机号格式错误')
        return data

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('两次输入密码不一致')
        return attrs

    def create(self, validated_data):
        user_up = self.context['request'].user
        if user_up.is_superuser:

            del validated_data['password2']
            user = UserProfile.objects.create(**validated_data)
            user.set_password(validated_data['password'])
            user.uid = make_uuid_code()
            user.auth_code = make_auth_code()
            user.login_token = make_login_token()
            user.is_active = False

            user.level = 2
            user.save()
            return user
        if not user_up.is_proxy:
            del validated_data['password2']
            user = UserProfile.objects.create(**validated_data)
            user.set_password(validated_data['password'])
            user.uid = make_uuid_code()
            user.auth_code = make_auth_code()
            user.login_token = make_login_token()
            user.is_active = False

            user.proxy_id = user_up.id
            user.is_proxy = True
            user.save()
            return user
        return user_up


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(label='密码', write_only=True, required=True, allow_blank=False, min_length=6,
                                     style={'input_type': 'password'}, help_text='密码')
    password2 = serializers.CharField(label='确认密码', write_only=True, required=True, allow_blank=False, min_length=6,
                                      style={'input_type': 'password'}, help_text='重复密码')

    class Meta:
        model = UserProfile
        fields = ['username', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('两次输入密码不一致')
        return attrs

    def update(self, instance, validated_data):
        del validated_data['password2']
        try:
            del validated_data['username']
            del validated_data['mobile']
        except:
            pass
        user_token = self.context['request'].session.get('token')
        user_dict = jwt_decode_handler(user_token)
        user_id = user_dict.get('user_id')
        user_queryset = UserProfile.objects.filter(id=user_id)
        if user_queryset:
            user = user_queryset[0]
            user.set_password(validated_data['password'])
            user.save()
            return user
        return instance


class ProxysSerializer(serializers.ModelSerializer):
    the_time = datetime.datetime.now() - datetime.timedelta(hours=1)
    today_time = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    yesterday_time = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    month_time = datetime.datetime(datetime.date.today().year, datetime.date.today().month, 1)
    add_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    # 今日收款金额 含 支付中 成功 关闭
    today_receive_all = serializers.SerializerMethodField(read_only=True)

    def get_today_receive_all(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='PAYING') | Q(pay_status='TRADE_SUCCESS') | Q(pay_status='TRADE_CLOSE'), user=obj,
            add_time__gte=self.today_time).aggregate(
            total_amount=Sum('total_amount'))
        return order_queryset.get('total_amount', 0)

    # 今日收款 仅含成功金额 有问题 如果订单是昨日 然后 今日到账的 那就不算了 所以今日订单数 成功 条件看 今日支付成功 还是 今日创建
    today_receive_success = serializers.SerializerMethodField(read_only=True)

    def get_today_receive_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='TRADE_SUCCESS'), user=obj,
            pay_time__gte=time.strftime('%Y-%m-%d', time.localtime(time.time()))).aggregate(
            total_amount=Sum('total_amount'))
        return order_queryset.get('total_amount', 0)

    # 今日总订单数 所有 包括成功与否
    today_count_num = serializers.SerializerMethodField(read_only=True)

    def get_today_count_num(self, obj):
        return OrderInfo.objects.filter(user=obj, add_time__gte=time.strftime('%Y-%m-%d',
                                                                              time.localtime(
                                                                                  time.time()))).all().count()

    # 今日订单数(成功) 有问题 如果订单是昨日 然后 今日到账的 那就不算了 所以今日订单数 成功 条件看 今日支付成功 还是 今日创建
    today_count_success_num = serializers.SerializerMethodField(read_only=True)

    def get_today_count_success_num(self, obj):
        return OrderInfo.objects.filter(user=obj, pay_status='TRADE_SUCCESS', add_time__gte=time.strftime('%Y-%m-%d',
                                                                                                          time.localtime(
                                                                                                              time.time()))).all().count()

    # 今日未付款订单数
    today_count_paying_num = serializers.SerializerMethodField(read_only=True)

    def get_today_count_paying_num(self, obj):
        return OrderInfo.objects.filter(user=obj, pay_status='PAYING', add_time__gte=time.strftime('%Y-%m-%d',
                                                                                                   time.localtime(
                                                                                                       time.time()))).all().count()

    # 总订单数 - 包括支付中
    total_count_num = serializers.SerializerMethodField(read_only=True)

    def get_total_count_num(self, obj):
        return OrderInfo.objects.filter(user=obj).all().count()

    # 总订单数(成功)
    total_count_success_num = serializers.SerializerMethodField(read_only=True)

    def get_total_count_success_num(self, obj):
        return OrderInfo.objects.filter(user=obj, pay_status='TRADE_SUCCESS').all().count()

    # 总订单数(失败)
    total_count_fail_num = serializers.SerializerMethodField(read_only=True)

    def get_total_count_fail_num(self, obj):
        return OrderInfo.objects.filter(user=obj, pay_status='TRADE_CLOSE').all().count()

    # 总未支付订单数(未支付)
    total_count_paying_num = serializers.SerializerMethodField(read_only=True)

    def get_total_count_paying_num(self, obj):
        return OrderInfo.objects.filter(user=obj, pay_status='PAYING').all().count()

    # 小时 datetime.datetime.now()-datetime.timedelta(hours=1)
    hour_total_num = serializers.SerializerMethodField(read_only=True)

    def get_hour_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
                                        add_time__gte=self.the_time).count()

    # 小时 成功数
    hour_success_num = serializers.SerializerMethodField(read_only=True)

    def get_hour_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__gte=self.the_time).count()

    # 小时 成功率
    hour_rate = serializers.SerializerMethodField(read_only=True)

    def get_hour_rate(self, obj):
        a = self.get_hour_success_num(obj)
        b = self.get_hour_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 小时总金额
    hour_money_all = serializers.SerializerMethodField(read_only=True)

    def get_hour_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  add_time__gte=self.the_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', '0')

    # 小时成功金额
    hour_money_success = serializers.SerializerMethodField(read_only=True)

    def get_hour_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='TRADE_SUCCESS'), user=obj,
            pay_time__gte=self.the_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 今天
    # 今天 datetime.datetime.now()-datetime.timedelta(hours=1)
    today_total_num = serializers.SerializerMethodField(read_only=True)

    def get_today_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
            add_time__gte=self.today_time).count()

    # 今天 成功数
    today_success_num = serializers.SerializerMethodField(read_only=True)

    def get_today_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__gte=self.today_time).count()

    # 今天 成功率
    today_rate = serializers.SerializerMethodField(read_only=True)

    def get_today_rate(self, obj):
        a = self.get_today_success_num(obj)
        b = self.get_today_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 今天总金额
    today_money_all = serializers.SerializerMethodField(read_only=True)

    def get_today_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  add_time__gte=self.today_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 今天成功金额
    today_money_success = serializers.SerializerMethodField(read_only=True)

    def get_today_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='TRADE_SUCCESS'), user=obj,
            pay_time__gte=self.today_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 昨天
    # 昨天 datetime.datetime.now()-datetime.timedelta(hours=1)
    yesterday_total_num = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
                                        add_time__gte=self.yesterday_time, add_time__lte=self.today_time).count()

    # 昨天 成功数
    yesterday_success_num = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__range=(self.yesterday_time, self.today_time)).count()

    # 昨天 成功率
    yesterday_rate = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_rate(self, obj):
        a = self.get_yesterday_success_num(obj)
        b = self.get_yesterday_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 昨天总金额
    yesterday_money_all = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  pay_time__range=(self.yesterday_time, self.today_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 昨天成功金额
    yesterday_money_success = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            pay_status='TRADE_SUCCESS', user=obj, pay_time__range=(self.yesterday_time, self.today_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 当月
    # 当月 datetime.datetime.now()-datetime.timedelta(hours=1)
    month_total_num = serializers.SerializerMethodField(read_only=True)

    def get_month_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
                                        add_time__gte=self.month_time).count()

    # 当月 成功数
    month_success_num = serializers.SerializerMethodField(read_only=True)

    def get_month_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__gte=self.month_time).count()

    # 当月 成功率
    month_rate = serializers.SerializerMethodField(read_only=True)

    def get_month_rate(self, obj):
        a = self.get_month_success_num(obj)
        b = self.get_month_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    #
    # 当月总金额
    month_money_all = serializers.SerializerMethodField(read_only=True)

    def get_month_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  pay_time__gte=(self.month_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    #
    # 当月成功金额
    month_money_success = serializers.SerializerMethodField(read_only=True)

    def get_month_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            pay_status='TRADE_SUCCESS', user=obj, pay_time__gte=(self.month_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 全部
    # 全部 datetime.datetime.now()-datetime.timedelta(hours=1)
    all_total_num = serializers.SerializerMethodField(read_only=True)

    def get_all_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj).count()

    # 全部 成功数
    all_success_num = serializers.SerializerMethodField(read_only=True)

    def get_all_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj).count()

    # 全部 成功率
    all_rate = serializers.SerializerMethodField(read_only=True)

    def get_all_rate(self, obj):
        a = self.get_all_success_num(obj)
        b = self.get_all_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 全部总金额
    all_money_all = serializers.SerializerMethodField(read_only=True)

    def get_all_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 全部成功金额
    all_money_success = serializers.SerializerMethodField(read_only=True)

    def get_all_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            pay_status='TRADE_SUCCESS', user=obj).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    value = serializers.SerializerMethodField(read_only=True)

    def get_value(self, obj):
        return obj.username

    label = serializers.SerializerMethodField(read_only=True)

    def get_label(self, obj):
        return obj.id

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'label', 'value', 'uid', 'auth_code', 'mobile', 'notify_url', 'is_proxy',
                  'is_active', 'add_time', 'total_money',
                  'total_count_num',
                  'total_count_success_num', 'total_count_fail_num', 'total_count_paying_num', 'today_receive_all',
                  'today_receive_success',
                  'today_count_num', 'today_count_success_num', 'today_count_paying_num', 'hour_total_num',
                  'hour_success_num', 'hour_rate', 'hour_money_all', 'hour_money_success', 'today_total_num',
                  'today_success_num', 'today_rate', 'today_money_all', 'today_money_success', 'yesterday_total_num',
                  'yesterday_success_num', 'yesterday_rate', 'yesterday_money_all', 'yesterday_money_success',
                  'month_total_num',
                  'month_success_num', 'month_rate', 'month_money_all', 'month_money_success', 'all_total_num',
                  'all_success_num', 'all_rate', 'all_money_all', 'all_money_success'
                  ]


class BankInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankInfo
        fields = '__all__'


class UserDetailSerializer(serializers.ModelSerializer):
    the_time = datetime.datetime.now() - datetime.timedelta(hours=1)
    today_time = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    yesterday_time = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    month_time = datetime.datetime(datetime.date.today().year, datetime.date.today().month, 1)
    add_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M',read_only=True)
    username = serializers.CharField(label='用户名', read_only=True, allow_blank=False, help_text='用户名')
    uid = serializers.CharField(label='用户uid', read_only=True, allow_blank=False, help_text='用户uid')
    mobile = serializers.CharField(label='手机号', read_only=True, allow_blank=False, help_text='手机号')
    auth_code = serializers.CharField(label='用户授权码', read_only=True, allow_blank=False, help_text='用户授权码')
    is_proxy = serializers.BooleanField(label='是否代理', read_only=True)
    total_money = serializers.CharField(read_only=True)
    proxys = ProxysSerializer(many=True, read_only=True)
    banks = BankInfoSerializer(many=True, read_only=True)

    add_money = serializers.DecimalField(max_digits=7, decimal_places=2, help_text='加款', write_only=True,
                                         required=False)
    minus_money = serializers.DecimalField(max_digits=7, decimal_places=2, help_text='扣款', write_only=True,
                                           required=False)

    is_active = serializers.BooleanField(label='是否激活', required=False)
    service_rate = serializers.CharField(read_only=True)

    def validate_add_money(self, data):
        if not re.match(r'(^[1-9]([0-9]{1,4})?(\.[0-9]{1,2})?$)|(^(0){1}$)|(^[0-9]\.[0-9]([0-9])?$)', str(data)):
            raise serializers.ValidationError('金额异常，请重新输入')
        if data == 0:
            raise serializers.ValidationError('金额异常，请重新输入')
        return data

    def validate_minus_money(self, data):
        if not re.match(r'(^[1-9]([0-9]{1,4})?(\.[0-9]{1,2})?$)|(^(0){1}$)|(^[0-9]\.[0-9]([0-9])?$)', str(data)):
            raise serializers.ValidationError('金额异常，请重新输入')
        if data == 0:
            raise serializers.ValidationError('金额异常，请重新输入')
        return data

    # 小时 datetime.datetime.now()-datetime.timedelta(hours=1)
    hour_total_num = serializers.SerializerMethodField(read_only=True)

    def get_hour_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
                                        add_time__gte=self.the_time).count()

    # 小时 成功数
    hour_success_num = serializers.SerializerMethodField(read_only=True)

    def get_hour_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__gte=self.the_time).count()

    # 小时 成功率
    hour_rate = serializers.SerializerMethodField(read_only=True)

    def get_hour_rate(self, obj):
        a = self.get_hour_success_num(obj)
        b = self.get_hour_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 小时总金额
    hour_money_all = serializers.SerializerMethodField(read_only=True)

    def get_hour_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  add_time__gte=self.the_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', '0')

    # 小时成功金额
    hour_money_success = serializers.SerializerMethodField(read_only=True)

    def get_hour_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='TRADE_SUCCESS'), user=obj,
            pay_time__gte=self.the_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 今天
    # 今天 datetime.datetime.now()-datetime.timedelta(hours=1)
    today_total_num = serializers.SerializerMethodField(read_only=True)

    def get_today_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
                                        add_time__gte=self.today_time).count()

    # 今天 成功数
    today_success_num = serializers.SerializerMethodField(read_only=True)

    def get_today_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__gte=self.today_time).count()

    # 今天 成功率
    today_rate = serializers.SerializerMethodField(read_only=True)

    def get_today_rate(self, obj):
        a = self.get_today_success_num(obj)
        b = self.get_today_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 今天总金额
    today_money_all = serializers.SerializerMethodField(read_only=True)

    def get_today_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  add_time__gte=self.today_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 今天成功金额
    today_money_success = serializers.SerializerMethodField(read_only=True)

    def get_today_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='TRADE_SUCCESS'), user=obj,
            pay_time__gte=self.today_time).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 昨天
    # 昨天 datetime.datetime.now()-datetime.timedelta(hours=1)
    yesterday_total_num = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
                                        add_time__gte=self.yesterday_time, add_time__lte=self.today_time).count()

    # 昨天 成功数
    yesterday_success_num = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__range=(self.yesterday_time, self.today_time)).count()

    # 昨天 成功率
    yesterday_rate = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_rate(self, obj):
        a = self.get_yesterday_success_num(obj)
        b = self.get_yesterday_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 昨天总金额
    yesterday_money_all = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  pay_time__range=(self.yesterday_time, self.today_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 昨天成功金额
    yesterday_money_success = serializers.SerializerMethodField(read_only=True)

    def get_yesterday_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            pay_status='TRADE_SUCCESS', user=obj, pay_time__range=(self.yesterday_time, self.today_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 当月
    # 当月 datetime.datetime.now()-datetime.timedelta(hours=1)
    month_total_num = serializers.SerializerMethodField(read_only=True)

    def get_month_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj,
                                        add_time__gte=self.month_time).count()

    # 当月 成功数
    month_success_num = serializers.SerializerMethodField(read_only=True)

    def get_month_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj,
                                        add_time__gte=self.month_time).count()

    # 当月 成功率
    month_rate = serializers.SerializerMethodField(read_only=True)

    def get_month_rate(self, obj):
        a = self.get_month_success_num(obj)
        b = self.get_month_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    #
    # 当月总金额
    month_money_all = serializers.SerializerMethodField(read_only=True)

    def get_month_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj,
                                                  pay_time__gte=(self.month_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    #
    # 当月成功金额
    month_money_success = serializers.SerializerMethodField(read_only=True)

    def get_month_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            pay_status='TRADE_SUCCESS', user=obj, pay_time__gte=(self.month_time)).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 全部
    # 全部 datetime.datetime.now()-datetime.timedelta(hours=1)
    all_total_num = serializers.SerializerMethodField(read_only=True)

    def get_all_total_num(self, obj):
        return OrderInfo.objects.filter(user=obj).count()

    # 全部 成功数
    all_success_num = serializers.SerializerMethodField(read_only=True)

    def get_all_success_num(self, obj):
        return OrderInfo.objects.filter(pay_status='TRADE_SUCCESS', user=obj).count()

    # 全部 成功率
    all_rate = serializers.SerializerMethodField(read_only=True)

    def get_all_rate(self, obj):
        a = self.get_all_success_num(obj)
        b = self.get_all_total_num(obj)
        if b == 0 or a == 0:
            return '0%'
        return ('{:.2%}'.format(a / b))

    # 全部总金额
    all_money_all = serializers.SerializerMethodField(read_only=True)

    def get_all_money_all(self, obj):
        order_queryset = OrderInfo.objects.filter(user=obj).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    # 全部成功金额
    all_money_success = serializers.SerializerMethodField(read_only=True)

    def get_all_money_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            pay_status='TRADE_SUCCESS', user=obj).aggregate(
            total_amount=Sum('total_amount'))
        if not order_queryset.get('total_amount', '0'):
            return '0'
        return order_queryset.get('total_amount', 0)

    class Meta:
        model = UserProfile
        fields = ['id','username', 'uid', 'auth_code', 'mobile', 'notify_url', 'total_money', 'is_proxy', 'is_active',
                  'proxys', 'banks',
                  'minus_money', 'add_money', 'service_rate','add_time', 'hour_total_num',
                  'hour_success_num', 'hour_rate', 'hour_money_all', 'hour_money_success', 'today_total_num',
                  'today_success_num', 'today_rate', 'today_money_all', 'today_money_success', 'yesterday_total_num',
                  'yesterday_success_num', 'yesterday_rate', 'yesterday_money_all', 'yesterday_money_success',
                  'month_total_num',
                  'month_success_num', 'month_rate', 'month_money_all', 'month_money_success', 'all_total_num',
                  'all_success_num', 'all_rate', 'all_money_all', 'all_money_success']
