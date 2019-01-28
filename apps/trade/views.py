import hashlib
import random
import re
import time
import datetime

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from decimal import Decimal
# Create your views here.
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets, status, views
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from trade.filters import WithDrawFilter
from trade.models import OrderInfo, WithDrawMoney
from trade.serializers import OrderSerializer, OrderListSerializer, BankinfoSerializer, WithDrawSerializer, \
    WithDrawCreateSerializer
from user.models import BankInfo, UserProfile
from utils.make_code import make_short_code
from utils.permissions import IsOwnerOrReadOnly


class OrderListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100


class OrderViewset(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = OrderSerializer
    pagination_class = OrderListPagination
    '状态,时间范围，金额范围'

    # filter_backends = (DjangoFilterBackend,)
    # filter_class = OrdersFilter

    def get_serializer_class(self):
        if self.action == "create":
            return OrderSerializer
        return OrderListSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return OrderInfo.objects.all().order_by('id')
        # elif not self.request.user.is_proxy:
        #     user_queryset = UserProfile.objects.filter(proxy_id=self.request.user.id)
        #     print('user_queryset',user_queryset)
        #     for user_obj in user_queryset:
        #         print('user_obj',OrderInfo.objects.filter(user_id=user_obj.id))
        # return [OrderInfo.objects.filter(user_id=user_obj.id).order_by('-add_time') for user_obj in user_queryset]
        user = self.request.user
        if user:
            return OrderInfo.objects.filter(user=self.request.user).order_by('-add_time')
        return []


class BankViewset(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet, mixins.UpdateModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = BankinfoSerializer
    pagination_class = OrderListPagination
    '状态,时间范围，金额范围'

    # filter_backends = (DjangoFilterBackend,)
    # filter_class = OrdersFilter

    def get_serializer_class(self):
        # if not self.request.user.is_proxy:
        if self.action == "create":
            return BankinfoSerializer
        return BankinfoSerializer

    # return []

    def get_queryset(self):
        if self.request.user.is_superuser:
            return BankInfo.objects.all().order_by('id')
        user = self.request.user
        if user:
            return BankInfo.objects.filter(user=self.request.user).order_by('-add_time')
        return []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not self.request.user.is_proxy:
            user = self.perform_create(serializer)
        response_data = serializer.data
        headers = self.get_success_headers(response_data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class GetPayView(views.APIView):
    def post(self, request):
        processed_dict = {}
        resp = {'msg': '操作成功'}
        for key, value in request.data.items():
            processed_dict[key] = value
        uid = processed_dict.get('uid', '')
        total_amount = processed_dict.get('total_amount', '')
        user_msg = processed_dict.get('user_msg', '')
        order_id = processed_dict.get('order_id', '')
        key = processed_dict.get('key', '')
        return_url = processed_dict.get('return_url', '')
        user_queryset = UserProfile.objects.filter(uid=uid)
        if not user_queryset:
            resp['msg'] = 'uid或者auth_code错误，请重试~~'
            return Response(resp, status=404)
        patt = re.match(r'(^[1-9]([0-9]{1,4})?(\.[0-9]{1,2})?$)|(^(0){1}$)|(^[0-9]\.[0-9]([0-9])?$)', total_amount)
        try:
            patt.group()
        except:
            resp['msg'] = '金额输入错误，请重试~~0.01到5万间'
            return Response(resp, status=404)
        if not order_id:
            resp['msg'] = '请填写订单号~~'
            return Response(resp, status=404)
        if not return_url:
            resp['msg'] = '请填写正确跳转url~~'
            return Response(resp, status=404)
        # 识别出 用户
        user = user_queryset[0]
        # 加密 uid + auth_code + total_amount + return_url + order_id
        auth_code = user.auth_code
        new_temp = str(uid + auth_code + total_amount + return_url + order_id)
        m = hashlib.md5()
        m.update(new_temp.encode('utf-8'))
        my_key = m.hexdigest()
        if my_key == key:
            short_code = make_short_code(8)
            order_no = "{time_str}{userid}{randstr}".format(time_str=time.strftime("%Y%m%d%H%M%S"),
                                                            userid=user.id, randstr=short_code)
            bank_queryet = BankInfo.objects.filter(is_active=True).all()
            if not bank_queryet:
                resp['code'] = 404
                resp['msg'] = '收款商户未激活'
                return Response(resp)

            # 关闭超时订单
            now_time = datetime.datetime.now() - datetime.timedelta(days=2)
            order_queryset = OrderInfo.objects.filter(pay_status='PAYING', add_time__lte=now_time).update(
                pay_status='TRADE_CLOSE')

            # 处理金额
            while True:
                order_queryset = OrderInfo.objects.filter(pay_status='PAYING', total_amount=total_amount)
                if not order_queryset:
                    break
                total_amount = (Decimal(total_amount) + Decimal(random.random())).quantize(Decimal('0.00'))
            print('total_amount', total_amount)

            # 随机抽一张收款卡
            bank_obj = random.choice(bank_queryet)
            name = bank_obj.name
            account_num = bank_obj.account_num
            bank_type = bank_obj.bank_type
            open_bank = bank_obj.open_bank
            bank_tel = bank_obj.bank_tel

            order = OrderInfo()
            order.user_id = user.id
            order.order_no = order_no
            order.pay_status = 'PAYING'
            order.total_amount = total_amount
            order.user_msg = user_msg
            order.order_id = order_id
            order.bank_tel = bank_tel
            order.account_num = account_num
            order.save()
            resp['msg'] = '创建成功'
            resp['code'] = 200
            resp['name'] = name
            resp['account_num'] = account_num
            resp['total_amount'] = total_amount
            resp['bank_type'] = bank_type
            resp['open_bank'] = open_bank
            return Response(resp)
        resp['code'] = 404
        resp['msg'] = 'key匹配错误'
        return Response(resp)


class VerifyView(views.APIView):
    def post(self, request):
        processed_dict = {}
        resp = {'msg': '操作成功'}
        for key, value in request.data.items():
            processed_dict[key] = value
        money = processed_dict.get('money', '')
        bank_tel = processed_dict.get('bank_tel', '')

        order_queryset = OrderInfo.objects.filter(pay_status='PAYING', total_amount=money, bank_tel=bank_tel)
        print('order_queryset', order_queryset)
        if len(order_queryset) == 1:
            order_obj = order_queryset[0]
            order_obj.pay_status = 'TRADE_SUCCESS'
            order_obj.pay_time = datetime.datetime.now()
            order_obj.save()
            user_id = order_obj.user_id
            user_obj = UserProfile.objects.filter(id=user_id)[0]
            account_num = order_obj.account_num
            bank_obj = BankInfo.objects.filter(account_num=account_num)[0]

            # 更新用户收款
            user_obj.total_money = '%.2f' % (user_obj.total_money + float(money))
            user_obj.save()

            # 更新商家存钱
            bank_obj.total_money = '%.2f' % (bank_obj.total_money + float(money))
            bank_obj.last_time = datetime.datetime.now()
            bank_obj.save()
            return Response(resp)
        elif not order_queryset:
            resp['msg'] = '订单不存在'
            return Response(resp)
        else:
            # 当post 过来的 订单 金额 和 银行电话 都相同时，存在多笔订单 无法识别
            resp['orders'] = []
            for order in order_queryset:
                new_dict = {'单号：': order.order_no, '订单时间：': order.add_time}
                resp['orders'].append(new_dict)
            resp['msg'] = '存在多笔订单，需手动处理'
            return Response(resp)


class AddMoney(views.APIView):
    def post(self, request):
        pass


class WithDrawViewset(mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                      mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = WithDrawSerializer
    pagination_class = OrderListPagination
    filter_backends = (DjangoFilterBackend,)
    filter_class = WithDrawFilter

    def get_serializer_class(self):
        if self.action == "retrieve":
            return WithDrawSerializer
        elif self.action == "create":
            return WithDrawCreateSerializer
        else:
            return WithDrawSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return WithDrawMoney.objects.all().order_by('-add_time')
        if not user.is_proxy:
            user_list = []
            user_queryset = UserProfile.objects.filter(proxy_id=user.id)
            print(len(user_queryset))

            if not user_queryset:
                return WithDrawMoney.objects.filter(user=self.request.user).order_by('-add_time')

            for user_obj in user_queryset:
                user_list.append(user_obj.id)
            print('user_list', user_list)
            return WithDrawMoney.objects.filter(user_id__in=user_list)


            # if len(user_queryset) == 1:
            #     return WithDrawMoney.objects.filter(Q(user=user_queryset[0])).order_by('-add_time')
            # elif len(user_queryset) == 2:
            #     return WithDrawMoney.objects.filter(Q(user=user_queryset[0]) | Q(user=user_queryset[1])).order_by('-add_time')
            # elif len(user_queryset) == 3:
            #     return WithDrawMoney.objects.filter(
            #         Q(user=user_queryset[0]) | Q(user=user_queryset[1]) | Q(user=user_queryset[2])).order_by('-add_time')
        if user:
            return WithDrawMoney.objects.filter(user=self.request.user).order_by('-add_time')
        return []

    def update(self, request, *args, **kwargs):
        resp = {'msg': []}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        withdraw_status = self.request.data.get('withdraw_status', '')
        withdraw_obj = self.get_object()
        user_obj = UserProfile.objects.filter(id=withdraw_obj.user_id)[0]
        if not user_obj.is_proxy:
            print('withdraw_status', withdraw_status)
            if withdraw_status:
                withdraw_obj.withdraw_status = withdraw_status
                resp['msg'].append('状态修改成功')
        else:
            resp['msg'].append('该用户没有操作权限')
        withdraw_obj.save()
        return Response(data=resp, status=status.HTTP_200_OK)
