# 用的时候使用OrderSerializer和OrderDetailSerializer，
import re
import time

from django.db.models import Sum, Count
from rest_framework import serializers, status
from time import strftime, localtime
from trade.models import OrderInfo, WithDrawMoney
from user.models import BankInfo, UserProfile
from utils.make_code import generate_order_no


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    # order_no = serializers.CharField(read_only=True)
    trade_no = serializers.CharField(read_only=True)
    pay_status = serializers.CharField(read_only=True)
    pay_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')

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

    def validate_account_num(self, data):
        bank_queryset = BankInfo.objects.filter(account_num=data)
        if bank_queryset:
            raise serializers.ValidationError("银行卡已存在")
        return data

    class Meta:
        model = BankInfo
        # fields = '__all__'
        fields = ['user', "id", "last_time", 'add_time', 'total_money', 'name', 'account_num', 'bank_type', 'open_bank',
                  'mobile', 'is_active', 'bank_tel', 'card_index', 'bank_mark']


class OrderListSerializer(serializers.ModelSerializer):
    pay_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    add_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    username = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.SerializerMethodField(read_only=True)

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

    class Meta:
        model = WithDrawMoney
        fields = ['id', 'user', 'receive_time', 'add_time', 'money', 'receive_way', 'bank_type', 'user_msg',
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
    time_rate =serializers.CharField(read_only=True)
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
