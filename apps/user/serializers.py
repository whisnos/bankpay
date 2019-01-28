import time

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_jwt.utils import jwt_decode_handler
import re

from trade.models import OrderInfo
from user.models import UserProfile, BankInfo
from django.db.models import Q

from utils.make_code import make_uuid_code, make_auth_code


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
        del validated_data['password2']
        user = UserProfile.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.uid = make_uuid_code()
        user.auth_code = make_auth_code()
        user.is_active = False
        user.save()
        return user


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
    # 今日收款金额
    today_receive_all = serializers.SerializerMethodField(read_only=True)

    def get_today_receive_all(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='PAYING') | Q(pay_status='TRADE_SUCCESS') | Q(pay_status='TRADE_CLOSE'), user=obj,
            add_time__gte=time.strftime('%Y-%m-%d', time.localtime(time.time())))
        all_num = 0
        for num in order_queryset:
            all_num += num.total_amount
        return str(all_num)

    # 今日收款 仅含成功金额 有问题 如果订单是昨日 然后 今日到账的 那就不算了 所以今日订单数 成功 条件看 今日支付成功 还是 今日创建
    today_receive_success = serializers.SerializerMethodField(read_only=True)

    def get_today_receive_success(self, obj):
        order_queryset = OrderInfo.objects.filter(
            Q(pay_status='TRADE_SUCCESS'), user=obj,
            add_time__gte=time.strftime('%Y-%m-%d', time.localtime(time.time())))
        all_num = 0
        for num in order_queryset:
            all_num += num.total_amount
        return str(all_num)

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

    class Meta:
        model = UserProfile
        fields = ['username', 'uid', 'auth_code', 'mobile', 'notify_url', 'is_proxy', 'total_money', 'total_count_num',
                  'total_count_success_num', 'total_count_fail_num', 'total_count_paying_num', 'today_receive_all','today_receive_success',
                  'today_count_num', 'today_count_success_num','today_count_paying_num']


class BankInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankInfo
        fields = '__all__'


class UserDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(label='用户名', read_only=True, allow_blank=False, help_text='用户名')
    uid = serializers.CharField(label='用户uid', read_only=True, allow_blank=False, help_text='用户uid')
    mobile = serializers.CharField(label='手机号', read_only=True, allow_blank=False, help_text='手机号')
    auth_code = serializers.CharField(label='用户授权码', read_only=True, allow_blank=False, help_text='用户授权码')
    total_money = serializers.CharField(read_only=True)
    proxys = ProxysSerializer(many=True, read_only=True)
    banks = BankInfoSerializer(many=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = ['username', 'uid', 'auth_code', 'mobile', 'notify_url', 'total_money', 'proxys', 'banks']
