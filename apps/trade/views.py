import hashlib
import json
import random
import re
import time
import datetime
from io import BytesIO

import requests
from django.contrib.auth.backends import ModelBackend
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

from trade.filters import WithDrawFilter, OrdersFilter
from trade.models import OrderInfo, WithDrawMoney
from trade.serializers import OrderSerializer, OrderListSerializer, BankinfoSerializer, WithDrawSerializer, \
    WithDrawCreateSerializer, VerifyPaySerializer, OrderUpdateSeralizer
from user.models import BankInfo, UserProfile, DeviceName
from utils.make_code import make_short_code
from utils.permissions import IsOwnerOrReadOnly


class OrderListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100

class CustomModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, type=None, **kwargs):
        print('username', request)
        try:
            user = DeviceName.objects.get(Q(username=username))
            if user.login_token == password:
                return user
            else:
                return None
        except Exception as e:
            return None
        # try:
        #     user = User.objects.get(Q(username=username) | Q(mobile=username))
        #     if user.check_password(password) or user.login_token == password:
        #         return user
        # except Exception as e:
        #     return None

class OrderViewset(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet, mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = OrderSerializer
    pagination_class = OrderListPagination
    '状态,时间范围，金额范围'

    filter_backends = (DjangoFilterBackend,)
    filter_class = OrdersFilter

    def get_serializer_class(self):
        if self.action == "create":
            return OrderSerializer
        elif self.action == "update":
            return OrderUpdateSeralizer
        return OrderListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return OrderInfo.objects.all().order_by('id')
        if not user.is_proxy:
            user_list = []
            user_queryset = UserProfile.objects.filter(proxy_id=user.id)

            if not user_queryset:
                return OrderInfo.objects.filter(user=self.request.user).order_by('-add_time')

            for user_obj in user_queryset:
                user_list.append(user_obj.id)
            return OrderInfo.objects.filter(Q(user_id__in=user_list) | Q(user=self.request.user)).order_by(
                '-add_time')
        if user:
            return OrderInfo.objects.filter(user=self.request.user).order_by('-add_time')
        return []

    def create(self, request, *args, **kwargs):
        user_up = self.request.user
        resp = {'msg': []}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if user_up.is_proxy:
            order = self.perform_create(serializer)
            print(111111)
            response_data = serializer.data
            headers = self.get_success_headers(response_data)
            code = 201
            return Response(response_data, status=code, headers=headers)
        code = 403
        resp['msg'] = '创建失败'
        return Response(data=resp, status=code)

    def update(self, request, *args, **kwargs):
        resp = {'msg': []}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_obj = self.get_object()
        code = 200
        if not self.request.user.is_proxy:
            pay_status = self.request.data.get('pay_status', '')
            print('pay_status', pay_status)
            if pay_status:
                order_obj.pay_status = pay_status
                code = 200
                resp['msg'].append('状态修改成功')
                order_obj.save()
        else:
            code = 403
            resp['msg'].append('该用户没有操作权限')
        return Response(data=resp, status=code)


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
            bank = self.perform_create(serializer)
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
        if not re.match(r'(^[1-9]([0-9]{1,4})?(\.[0-9]{1,2})?$)|(^(0){1}$)|(^[0-9]\.[0-9]([0-9])?$)',
                        str(total_amount)):
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
        new_temp = str(str(uid) + str(auth_code) + str(total_amount) + str(return_url) + str(order_id))
        m = hashlib.md5()
        m.update(new_temp.encode('utf-8'))
        my_key = m.hexdigest()
        if my_key == key:
            short_code = make_short_code(8)
            order_no = "{time_str}{userid}{randstr}".format(time_str=time.strftime("%Y%m%d%H%M%S"),
                                                            userid=user.id, randstr=short_code)

            bank_queryet = BankInfo.objects.filter(is_active=True, user_id=user.proxy_id).all()
            if not bank_queryet:
                resp['code'] = 404
                resp['msg'] = '收款商户未激活'
                return Response(resp)

            # 关闭超时订单
            now_time = datetime.datetime.now() - datetime.timedelta(minutes=10)
            order_queryset = OrderInfo.objects.filter(pay_status='PAYING', add_time__lte=now_time).update(
                pay_status='TRADE_CLOSE')

            # # 处理金额
            while True:
                for bank in bank_queryet:
                    order_queryset = OrderInfo.objects.filter(pay_status='PAYING', total_amount=total_amount,
                                                              bank_tel=bank.bank_tel)
                    if not order_queryset:
                        name = bank.name
                        account_num = bank.account_num
                        bank_type = bank.bank_type
                        open_bank = bank.open_bank
                        bank_tel = bank.bank_tel
                        bank_mark = bank.bank_mark
                        card_index = bank.card_index
                        break
                    else:
                        continue
                if order_queryset:
                    total_amount = (Decimal(total_amount) + Decimal(random.uniform(-0.9, 0.9))).quantize(
                        Decimal('0.00'))
                else:
                    break

            print('total_amount', total_amount)
            order = OrderInfo()
            order.user_id = user.id
            order.order_no = order_no
            order.pay_status = 'PAYING'
            order.total_amount = total_amount
            order.user_msg = user_msg
            order.order_id = order_id
            order.bank_tel = bank_tel
            order.account_num = account_num
            order.pay_url = 'https://www.alipay.com/?appId=09999988&actionType=toCard&sourceId=bill&cardNo=请勿修改***金额&bankAccount=' + name + '&' + 'amount=' + str(
                total_amount) + '&bankMark=' + str(bank_mark) + '&bankName=' + bank_type + '&cardIndex=' + str(
                card_index) + '&cardNoHidden=true&cardChannel=HISTORY_CARD&orderSource=from'
            order.save()
            resp['msg'] = '创建成功'
            resp['code'] = 200
            resp['name'] = name
            resp['account_num'] = account_num
            resp['total_amount'] = total_amount
            resp['bank_type'] = bank_type
            resp['open_bank'] = open_bank
            resp['pay_url'] = 'https://' + request.META['HTTP_HOST'] + '/pay/?id=' + order_no
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
        key = processed_dict.get('key', '')
        new_temp = money + bank_tel
        m = hashlib.md5()
        m.update(new_temp.encode('utf-8'))
        my_key = m.hexdigest()
        if key == my_key:
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
                user_obj.total_money = '%.2f' % (Decimal(user_obj.total_money) + Decimal(money))
                user_obj.save()

                # 更新商家存钱
                bank_obj.total_money = '%.2f' % (Decimal(bank_obj.total_money) + Decimal(money))
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
        resp['msg'] = '无权限'
        return Response(resp)


class VerifyViewset(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    queryset = OrderInfo.objects.all()
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = VerifyPaySerializer

    def update(self, request, *args, **kwargs):
        user = self.request.user
        resp = {'msg': '操作成功'}
        if not user.is_proxy:
            processed_dict = {}
            for key, value in self.request.data.items():
                processed_dict[key] = value
            money = processed_dict.get('total_amount', '')
            bank_tel = processed_dict.get('bank_tel', '')
            key = processed_dict.get('key', '')
            bank_queryset = BankInfo.objects.filter(user_id=user.id, bank_tel=bank_tel)
            if len(bank_queryset) == 1:
                bank_obj = bank_queryset[0]

            elif not bank_queryset:
                code = 400
                resp['msg'] = '银行卡不存在，联系管理员处理'
                return Response(data=resp, status=code)

            else:
                resp['msg'] = '存在多张银行卡，需手动处理'
                code = 400
                return Response(data=resp, status=code)

            order_queryset = OrderInfo.objects.filter(pay_status='PAYING', total_amount=money,
                                                      account_num=bank_obj.account_num)
            if len(order_queryset) == 1:
                print('111111111111')
                order_obj = order_queryset[0]
            elif not order_queryset:
                code = 400
                resp['msg'] = '订单不存在，联系管理员处理'
                return Response(data=resp, status=code)

            else:
                resp['msg'] = '存在多笔订单，需手动处理'
                code = 400
                return Response(data=resp, status=code)

            new_temp = str(money) + str(bank_tel) + str(order_obj.order_no)
            m = hashlib.md5()
            m.update(new_temp.encode('utf-8'))
            my_key = m.hexdigest()
            if key == my_key:
                print(22222222222)
                order_obj = order_queryset[0]
                order_obj.pay_status = 'TRADE_SUCCESS'
                order_obj.pay_time = datetime.datetime.now()
                order_obj.save()
                user_id = order_obj.user_id
                user_obj = UserProfile.objects.filter(id=user_id)[0]
                account_num = order_obj.account_num
                bank_obj = BankInfo.objects.filter(account_num=account_num)[0]

                # 更新用户收款
                user_obj.total_money = '%.2f' % (Decimal(user_obj.total_money) + Decimal(money))
                user_obj.save()

                # 更新商家存钱
                bank_obj.total_money = '%.2f' % (Decimal(bank_obj.total_money) + Decimal(money))
                bank_obj.last_time = datetime.datetime.now()
                bank_obj.save()
                notify_url = user_obj.notify_url
                if not notify_url:
                    return Response('success')
                data_dict = {}
                data_dict['pay_status'] = order_obj.pay_status
                data_dict['add_time'] = str(order_obj.add_time)
                data_dict['pay_time'] = str(order_obj.pay_time)
                data_dict['total_amount'] = str(order_obj.total_amount)
                data_dict['order_id'] = order_obj.order_id
                data_dict['order_no'] = order_obj.order_no
                data_dict['user_msg'] = order_obj.user_msg
                resp['data'] = data_dict
                r = json.dumps(resp)
                headers = {'Content-Type': 'application/json'}
                try:
                    res = requests.post(notify_url, headers=headers, data=r, timeout=5, stream=True)
                    if res.text =='success':
                        return Response(data=resp, status=200)
                    else:
                        order_obj.pay_status = 'NOTICE_FAIL'
                        order_obj.save()
                        return Response(data=resp, status=400)
                except Exception:
                    order_obj.pay_status = 'NOTICE_FAIL'
                    order_obj.save()
                    return Response(data='状态异常',status=404)

        code = 403
        resp['msg'] = '无操作权限'
        return Response(data=resp, status=code)


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

    def get_permissions(self):
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        elif self.action == "create":
            return [IsAuthenticated()]
        else:
            return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return WithDrawMoney.objects.all().order_by('-add_time')
        if not user.is_proxy:
            user_list = []
            user_queryset = UserProfile.objects.filter(proxy_id=user.id)

            if not user_queryset:
                return WithDrawMoney.objects.filter(user=self.request.user).order_by('-add_time')

            for user_obj in user_queryset:
                user_list.append(user_obj.id)
            return WithDrawMoney.objects.filter(Q(user_id__in=user_list) | Q(user=self.request.user)).order_by(
                '-add_time')

        if user:
            return WithDrawMoney.objects.filter(user=self.request.user).order_by('-add_time')
        return []

    def create(self, request, *args, **kwargs):
        user_up = self.request.user
        resp = {'msg': []}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if user_up.is_proxy:
            order = self.perform_create(serializer)
            print(111111)
            response_data = serializer.data
            headers = self.get_success_headers(response_data)
            code = 201
            return Response(response_data, status=code, headers=headers)
        code = 403
        resp['msg'] = '创建失败'
        return Response(data=resp, status=code)

    def update(self, request, *args, **kwargs):
        resp = {'msg': []}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        withdraw_obj = self.get_object()
        code = 200
        if not self.request.user.is_proxy:
            withdraw_status = self.request.data.get('withdraw_status', '')
            print('withdraw_status', withdraw_status)
            if withdraw_status:
                withdraw_obj.withdraw_status = withdraw_status
                code = 200
                resp['msg'].append('状态修改成功')
                withdraw_obj.save()
        else:
            code = 403
            resp['msg'].append('该用户没有操作权限')
        return Response(data=resp, status=code)


import base64
import qrcode


def pay(request):
    # if request.method == 'POST':
    pay_url = request.get_full_path()
    url_list = pay_url.split('/pay/?id=')
    if len(url_list) == 2:
        order_no = url_list[1]
        if order_no:
            the_time = datetime.datetime.now() - datetime.timedelta(minutes=10)
            order_queryset = OrderInfo.objects.filter(order_no=order_no, add_time__gte=the_time)
            if order_queryset:
                pay_url = order_queryset[0].pay_url
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(pay_url)
                qr.make(fit=True)
                img = qr.make_image()
                output_buffer = BytesIO()
                img.save(output_buffer, format='JPEG')
                binary_data = output_buffer.getvalue()
                base64_data = base64.b64encode(binary_data)
                print('pay_url', base64_data)
                a = (b'data:image/png;base64,' + (base64_data)).decode('utf-8')
                return render(request, 'pay.html', {
                    "pay_url": a
                })
            else:
                return HttpResponse('订单失效')
        else:
            return HttpResponse('链接错误')
    else:
        return HttpResponse('链接错误')
