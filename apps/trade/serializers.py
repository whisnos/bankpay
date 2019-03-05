# 用的时候使用OrderSerializer和OrderDetailSerializer，
import re
import time

from django.db.models import Sum, Count
from rest_framework import serializers, status
from time import strftime, localtime

from rest_framework.validators import UniqueValidator

from trade.models import OrderInfo, WithDrawMoney
from user.models import BankInfo, UserProfile, DeviceName
from utils.make_code import generate_order_no, make_auth_code, make_login_token


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    # order_no = serializers.CharField(read_only=True)
    trade_no = serializers.CharField(read_only=True)
    pay_status = serializers.CharField(read_only=True)
    pay_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    account_num = serializers.CharField(read_only=True, )
    pay_url = serializers.CharField(read_only=True, )

    class Meta:
        model = OrderInfo
        fields = '__all__'


class OrderUpdateSeralizer(serializers.ModelSerializer):
    class Meta:
        model = OrderInfo
        fields = ['pay_status']


class BankinfoSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    last_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    total_money = serializers.CharField(read_only=True)
    account_num = serializers.CharField(label='银行卡号')
    mobile = serializers.CharField(label='手机号')
    devices_name = serializers.SerializerMethodField(read_only=True)
    devices = serializers.CharField(label='所属设备')

    # is_active = serializers.CharField(label='是否激活', required=False)

    def get_devices_name(self, obj):
        device_queryset = DeviceName.objects.filter(id=obj.devices_id)
        if device_queryset:
            return device_queryset[0].username
        return '未找到相应设备'

    def validate_mobile(self, data):
        if not re.match(r'^1([38][0-9]|4[579]|5[0-3,5-9]|6[6]|7[0135678]|9[89])\d{8}$', data):
            raise serializers.ValidationError('手机号格式错误')
        return data

    # devices = serializers.ChoiceField(label='所属设备',choices='QUESTION_TYPES')

    def validate_devices(self, obj):
        if not re.match(r'^(\+)?[1-9][0-9]*$', obj):
            raise serializers.ValidationError('格式错误')
        device_queryset = DeviceName.objects.filter(id=obj)
        if not device_queryset:
            raise serializers.ValidationError('对应设备不存在')
        obj = device_queryset[0]

        return obj

    def validate_account_num(self, data):
        bank_queryset = BankInfo.objects.filter(account_num=data)
        if bank_queryset:
            raise serializers.ValidationError("银行卡已存在")
        return data

    # def validate_is_active(self, obj):
    #     if str(obj) not in ['0', '1']:
    #         raise serializers.ValidationError('传值错误')
    #     return obj

    class Meta:
        model = BankInfo
        fields = '__all__'
        # fields = ['user', "id", "last_time", 'add_time', 'total_money', 'name', 'account_num', 'bank_type', 'open_bank',
        #           'mobile', 'is_active', 'bank_tel', 'card_index', 'bank_mark', 'devices', 'devices_name']


class UpdateBankinfoSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    last_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    total_money = serializers.CharField(read_only=True)
    account_num = serializers.CharField(label='银行卡号', required=False)
    bank_type = serializers.CharField(label='银行类型', required=False)
    # is_active = serializers.CharField(label='是否激活', required=False)
    name = serializers.CharField(label='姓名', required=False)
    mobile = serializers.CharField(label='手机', required=False)
    devices = serializers.CharField(label='所属设备', required=False)

    def validate_mobile(self, data):
        if not re.match(r'^1([38][0-9]|4[579]|5[0-3,5-9]|6[6]|7[0135678]|9[89])\d{8}$', data):
            raise serializers.ValidationError('手机号格式错误')
        return data

    def validate_name(self, data):
        user = self.context['request'].user
        bank_queryset = BankInfo.objects.filter(name=data, user_id=user.id)
        if bank_queryset and bank_queryset.exclude(id=bank_queryset[0].id):
            raise serializers.ValidationError("姓名已存在")
        return data

    # def validate_is_active(self, obj):
    #     if str(obj) not in ['0', '1']:
    #         raise serializers.ValidationError('传值错误')
    #     return obj

    def validate_account_num(self, data):
        bank_queryset = BankInfo.objects.filter(account_num=data)
        if bank_queryset and bank_queryset.exclude(id=bank_queryset[0].id):
            raise serializers.ValidationError("银行卡已存在")
        # if bank_queryset:
        #     raise serializers.ValidationError("银行卡已存在")
        return data

    def validate_devices(self, obj):
        if not re.match(r'^(\+)?[1-9][0-9]*$', obj):
            raise serializers.ValidationError('格式错误')
        device_queryset = DeviceName.objects.filter(id=obj)
        if not device_queryset:
            raise serializers.ValidationError('对应设备不存在')
        obj = device_queryset[0]

        return obj

    class Meta:
        model = BankInfo
        fields = '__all__'


class OrderListSerializer(serializers.ModelSerializer):
    pay_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    username = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.SerializerMethodField(read_only=True)
    total_amount = serializers.FloatField(read_only=True)

    def get_username(self, obj):
        user_queryset = UserProfile.objects.filter(id=obj.user_id)
        if user_queryset:
            return user_queryset[0].username
        return

    def get_user_id(self, obj):
        return str(obj.user_id)

    class Meta:
        model = OrderInfo
        fields = ['id', 'user_id', 'username', 'pay_status', 'total_amount', 'order_no', 'pay_time', 'add_time',
                  'order_id']


class GetPaySerializer(serializers.Serializer):
    uidd = serializers.CharField()
    order_no = serializers.CharField()
    trade_no = serializers.CharField()
    pay_status = serializers.CharField()
    pay_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M')

    # 生成订单号信息
    def generate_order_sn(self):
        import time
        from random import randint
        # "当前时间+userid+随机数"
        print(self.context, 6666666666666666)
        from utils.make_code import make_short_code
        short_code = make_short_code(8)
        order_sn = "{time_str}{userid}{randstr}".format(time_str=time.strftime("%Y%m%d%H%M%S"),
                                                        userid=self.context['request'].user.id, randstr=short_code)
        print('生成订单号信息+++++++++', order_sn)
        return order_sn

    def validate(self, attrs):
        # 添加订单
        attrs["order_no"] = self.generate_order_sn()
        return attrs


class WithDrawSerializer(serializers.ModelSerializer):
    # user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user = serializers.CharField(read_only=True)
    receive_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    money = serializers.FloatField(read_only=True)
    receive_way = serializers.CharField(read_only=True)
    bank_type = serializers.CharField(read_only=True)
    user_msg = serializers.CharField(read_only=True)
    receive_account = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    withdraw_no = serializers.CharField(read_only=True)
    time_rate = serializers.FloatField(read_only=True)
    real_money = serializers.FloatField(read_only=True)
    open_bank = serializers.CharField(read_only=True)

    class Meta:
        model = WithDrawMoney
        fields = ['id', 'user', 'receive_time', 'add_time', 'money', 'receive_way', 'bank_type', 'open_bank',
                  'user_msg',
                  'receive_account', 'full_name', 'withdraw_no', 'time_rate', 'withdraw_status', 'real_money']

        # fields = '__all__'


class WithDrawCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    withdraw_status = serializers.CharField(read_only=True)
    withdraw_no = serializers.CharField(read_only=True)
    receive_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    freeze_money = serializers.FloatField(read_only=True)
    money = serializers.FloatField()
    real_money = serializers.FloatField(read_only=True)
    time_rate = serializers.CharField(read_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        user_money = user.total_money
        if not re.match(r'(^[1-9]([0-9]{1,4})?(\.[0-9]{1,2})?$)|(^(0){1}$)|(^[0-9]\.[0-9]([0-9])?$)',
                        str(attrs['money'])):
            raise serializers.ValidationError('金额输入异常')
        if attrs['money'] > user_money or attrs['money'] == 0:
            raise serializers.ValidationError('金额输入异常')

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        user_money = user.total_money
        money = validated_data['money']
        if money <= user_money:
            validated_data['real_money'] = '%.2f' % (money * (1 - user.service_rate))
            with_model = WithDrawMoney.objects.create(**validated_data)
            withdraw_no = generate_order_no(user.id)
            with_model.withdraw_no = withdraw_no
            with_model.freeze_money = money
            with_model.time_rate = user.service_rate
            user.total_money = '%.2f' % (user_money - money)
            user.save()
            with_model.save()
            return with_model

    class Meta:
        model = WithDrawMoney
        fields = '__all__'


from django.db.models import Q


class TotalNumSerializer(serializers.Serializer):
    total = serializers.SerializerMethodField(read_only=True)

    def get_total(self, obj):
        user = self.context['request'].user
        old_time = OrderInfo.objects.filter(user=user).order_by('add_time')[0].add_time.strftime('%Y-%m-%d %H:%M:%S')
        local_time = strftime('%Y-%m-%d %H:%M:%S', localtime())
        min_time = self.context['request'].GET.get('min_time', old_time)
        max_time = self.context['request'].GET.get('max_time', local_time)
        if not min_time:
            min_time = old_time
        elif not max_time:
            max_time = local_time
        a = OrderInfo.objects.filter(Q(pay_status__icontains='TRADE_SUCCESS') | Q(pay_status__icontains='NOTICE_FAIL'),
                                     user=user, add_time__gte=min_time, add_time__lte=max_time,
                                     ).aggregate(Sum('total_amount'))
        b = OrderInfo.objects.filter(Q(pay_status__icontains='TRADE_SUCCESS') | Q(pay_status__icontains='NOTICE_FAIL'),
                                     user=user, add_time__gte=min_time, add_time__lte=max_time).aggregate(Count('id'))
        a.update(b)
        return (a)


class VerifyPaySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderInfo
        fields = '__all__'


class DeviceSerializer(serializers.ModelSerializer):
    # user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user = serializers.CharField(read_only=True)
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    auth_code = serializers.CharField(label='识别码', read_only=True, validators=[
        UniqueValidator(queryset=DeviceName.objects.all(), message='识别码不能重复')
    ], help_text='用户识别码')
    login_token = serializers.CharField(label='登录码', read_only=True, validators=[
        UniqueValidator(queryset=DeviceName.objects.all(), message='登录码不能重复')
    ], help_text='用户登录码')

    # username = serializers.SerializerMethodField(read_only=True)
    # def get_username(self, obj):
    #     user_queryset = UserProfile.objects.filter(id=obj.user_id)
    #     if user_queryset:
    #         return user_queryset[0].username
    #     return
    class Meta:
        model = DeviceName
        fields = '__all__'


class RegisterDeviceSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    username = serializers.CharField(label='用户名', required=True, min_length=5, max_length=20, allow_blank=False,
                                     validators=[
                                         UniqueValidator(queryset=UserProfile.objects.all(), message='用户名不能重复')
                                     ], help_text='用户名')
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    auth_code = serializers.CharField(label='识别码', read_only=True, validators=[
        UniqueValidator(queryset=DeviceName.objects.all(), message='识别码不能重复')
    ], help_text='用户识别码')
    login_token = serializers.CharField(label='登录码', read_only=True, validators=[
        UniqueValidator(queryset=DeviceName.objects.all(), message='登录码不能重复')
    ], help_text='用户登录码')

    def validate_username(self, obj):
        device_queryset = DeviceName.objects.filter(username=obj)
        if device_queryset:
            print(8888)
            raise serializers.ValidationError('用户名已存在')
        return obj

    # def create(self, validated_data):
    #     user_up = self.context['request'].user
    #     if user_up.is_superuser:
    #         user_id = validated_data.get('id')
    #         if user_id:
    #             user_queryset = UserProfile.objects.filter(id=user_id)
    #             if user_queryset:
    #                 device_obj = DeviceName.objects.create(**validated_data)
    #                 device_obj.auth_code = make_auth_code()
    #                 device_obj.login_token = make_login_token()
    #                 device_obj.is_active = validated_data.get('is_active')
    #                 device_obj.user_id = user_queryset[0].id
    #                 print('超级管理员创建设备成功')
    #                 device_obj.save()
    #         print('超级管理员创建设备失败')
    #         return user_up
    #     if not user_up.is_proxy:
    #         device_obj = DeviceName.objects.create(**validated_data)
    #         device_obj.auth_code = make_auth_code()
    #         device_obj.login_token = make_login_token()
    #         device_obj.is_active = validated_data.get('is_active')
    #
    #         device_obj.proxy_id = user_up.id
    #         device_obj.save()
    #         return device_obj
    #     return user_up

    class Meta:
        model = DeviceName
        fields = '__all__'


class UpdateDeviceSerializer(serializers.ModelSerializer):
    user=serializers.HiddenField(default=serializers.CurrentUserDefault())
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    auth_code = serializers.CharField(label='识别码', required=False, validators=[
        UniqueValidator(queryset=DeviceName.objects.all(), message='识别码不能重复')
    ], help_text='用户识别码')
    login_token = serializers.CharField(label='登录码', required=False, validators=[
        UniqueValidator(queryset=DeviceName.objects.all(), message='登录码不能重复')
    ], help_text='用户登录码')
    # username = serializers.CharField(label='设备名', required=False, min_length=5, max_length=20, allow_blank=False,
    #                                  validators=[
    #                                      UniqueValidator(queryset=UserProfile.objects.all(), message='设备名不能重复')
    #                                  ], help_text='设备名')
    username = serializers.CharField(label='设备名', read_only=True)
    is_active = serializers.CharField(label='是否激活', required=False)

    def validate_is_active(self, obj):
        if str(obj) not in ['0', '1']:
            raise serializers.ValidationError('传值错误')
        return obj

    # def validate_username(self, obj):
    #     device_queryset = DeviceName.objects.filter(username=obj)
    #     if device_queryset:
    #         raise serializers.ValidationError('用户名已存在')
    #     return obj

    # def validate_auth_code(self, obj):
    #     if obj:
    #         obj = make_auth_code()
    #     return obj
    #
    # def validate_login_token(self, obj):
    #     if obj:
    #         obj = make_login_token()
    #     return obj

    class Meta:
        model = DeviceName
        fields = '__all__'


class ReleaseSerializer(serializers.ModelSerializer):
    pay_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M',read_only=True)
    add_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M',read_only=True)
    username = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.SerializerMethodField(read_only=True)
    total_amount = serializers.FloatField(read_only=True)
    s_time = serializers.DateTimeField(write_only=True)
    e_time = serializers.DateTimeField(write_only=True)
    dele_type = serializers.CharField(write_only=True)
    safe_code = serializers.CharField(write_only=True)
    def get_username(self, obj):
        user_queryset = UserProfile.objects.filter(id=obj.user_id)
        if user_queryset:
            return user_queryset[0].username
        return

    def get_user_id(self, obj):
        return str(obj.user_id)

    def validate(self, attrs):
        print(11111111111,attrs)
        s_time=attrs.get('s_time')
        e_time=attrs.get('e_time')
        dele_type=attrs.get('dele_type')
        if s_time:
            if not re.match(r'(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2})', str(s_time)):
                raise serializers.ValidationError('时间格式错误，请重新输入')
        if e_time:
            if not re.match(r'(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2})', str(e_time)):
                raise serializers.ValidationError('时间格式错误，请重新输入')
        if str(dele_type) not in ['order', 'money']:
            raise serializers.ValidationError('传值错误')
        return attrs

    class Meta:
        model = OrderInfo
        fields = ['id', 'user_id', 'username', 'total_amount', 'pay_time', 'add_time',
                  'order_id','s_time','e_time','dele_type','safe_code']