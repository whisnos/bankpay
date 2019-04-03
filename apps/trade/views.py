import hashlib, json, random, re, time, datetime, requests
from io import BytesIO

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from decimal import Decimal
# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
# from import_export.admin import ExportMixin
from rest_framework import mixins, viewsets, filters, views, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from pay.settings import FONT_DOMAIN, CLOSE_TIME, SECRET_VERIFY
from trade.filters import WithDrawFilter, OrdersFilter, BankFilter
from trade.models import OrderInfo, WithDrawMoney
from trade.serializers import OrderSerializer, OrderListSerializer, BankinfoSerializer, WithDrawSerializer, \
    WithDrawCreateSerializer, VerifyPaySerializer, OrderUpdateSeralizer, DeviceSerializer, RegisterDeviceSerializer, \
    UpdateDeviceSerializer, UpdateBankinfoSerializer, ReleaseSerializer, BankListinfoSerializer, OrderGetSerializer
from user.filters import DeviceFilter
from user.models import BankInfo, UserProfile, DeviceName, OperateLog
# from user.views import MyThrottle
# from utils.make_class import ChooseChannel
from utils.make_code import make_short_code, make_auth_code, make_login_token, make_md5, generate_order_no
from utils.permissions import IsOwnerOrReadOnly, MakeLogs


class OrderListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    # max_page_size = 100000


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


from trade.models import OrderInfo
from drf_renderer_xlsx.renderers import XLSXRenderer
from drf_renderer_xlsx.mixins import XLSXFileMixin
from rest_framework import renderers


class OrderViewset(XLSXFileMixin, mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = OrderSerializer
    pagination_class = OrderListPagination
    '状态,时间范围，金额范围'

    filter_backends = (DjangoFilterBackend,)
    filter_class = OrdersFilter
    renderer_classes = (renderers.JSONRenderer, XLSXRenderer, renderers.BrowsableAPIRenderer)

    column_header = {
        'titles': [
            "订单id",
            "用户id",
            "用户名",
            "支付状态",
            "金额",
            "商户订单号",
            "支付时间",
            "创建时间",
            "订单编号",
        ]
    }

    def get_serializer_class(self):
        if self.action == "create":
            return OrderSerializer
        elif self.action == "update":
            return OrderUpdateSeralizer
        return OrderListSerializer

    def get_queryset(self):
        user = self.request.user

        # 关闭超时订单
        now_time = datetime.datetime.now() - datetime.timedelta(minutes=CLOSE_TIME)
        OrderInfo.objects.filter(pay_status='PAYING', add_time__lte=now_time).update(
            pay_status='TRADE_CLOSE')

        if user.is_superuser:
            return OrderInfo.objects.all().order_by('-add_time')
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
            self.perform_create(serializer)
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


class BankViewset(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet, mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin, mixins.RetrieveModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = BankinfoSerializer
    pagination_class = OrderListPagination
    '状态,时间范围，金额范围'

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_class = BankFilter
    search_fields = ('account_num', 'name', 'mobile')

    def get_serializer_class(self):
        if self.action == "create":
            return BankinfoSerializer
        elif self.action == "update":
            return UpdateBankinfoSerializer
        elif self.action == "list":
            return BankListinfoSerializer
        return BankinfoSerializer

    # return []

    def get_queryset(self):
        if self.request.user.is_superuser:
            return BankInfo.objects.all().order_by('-add_time')
        user = self.request.user
        if user:
            return BankInfo.objects.filter(user=self.request.user).order_by('-add_time')
        return []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not self.request.user.is_proxy:
            name = request.data.get('name', '')
            bank_tel = request.data.get('bank_tel', '')
            mobile = request.data.get('mobile', '')
            print('9999999999', name, bank_tel, mobile)
            # 创建银行卡 根据 姓名 手机号 银行卡官方电话 若能找出 则不可创建
            bank_queryset = BankInfo.objects.filter(bank_tel=bank_tel, name=name, mobile=mobile)
            if not bank_queryset:
                code = 201
                bank = self.perform_create(serializer)
                response_data = {'msg': '创建成功'}
                headers = self.get_success_headers(response_data)
                return Response(response_data, status=code, headers=headers)

        code = 400
        response_data = {'msg': '创建失败'}
        headers = self.get_success_headers(response_data)
        return Response(response_data, status=code, headers=headers)

    def destroy(self, request, *args, **kwargs):
        if self.request.user.is_superuser or not self.request.user.is_proxy:
            instance = self.get_object()
            print(88888888888, instance)
            response_data = {'msg': '删除成功', 'id': instance.id}
            self.perform_destroy(instance)
            code = 204
            return Response(response_data, status=code)
        else:
            code = 403
            response_data = {'msg': '没有权限'}
        return Response(response_data, status=code)
    # def update(self, request, *args, **kwargs):
    #     resp = {'msg': []}
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     code = 200
    #     if not self.request.user.is_proxy:
    #         get_deviceid = self.request.data.get('id', '')
    #         name = self.request.data.get('name', '')
    #         is_active = self.request.data.get('is_active', '')
    #         account_num = self.request.data.get('account_num', '')
    #         bank_type = self.request.data.get('bank_type', '')
    #         open_bank = self.request.data.get('open_bank', '')
    #         mobile = self.request.data.get('mobile', '')
    #         # tuoxie 修改 银行卡
    #         if not self.request.user.is_proxy:
    #             if get_deviceid:
    #                 id_list = [bankinfo_obj.id for bankinfo_obj in BankInfo.objects.filter(user_id=self.request.user.id)]
    #                 if int(get_deviceid) in id_list:
    #                     bankinfo_obj=BankInfo.objects.get(id=get_deviceid)
    #                     if is_active:
    #                         if is_active == 'true':
    #                             is_active = True
    #                         if is_active == 'false':
    #                             is_active = False
    #                         bankinfo_obj.is_active = is_active
    #                         resp['msg'].append('状态修改成功')
    #                     if name:
    #                         bankinfo_obj.name = name
    #                         resp['msg'].append('姓名修改成功')
    #                     if account_num:
    #                         bankinfo_obj.account_num = account_num
    #                         resp['msg'].append('账号修改成功')
    #                     if bank_type:
    #                         bankinfo_obj.bank_type = bank_type
    #                         resp['msg'].append('银行类型修改成功')
    #                     if open_bank:
    #                         bankinfo_obj.open_bank = open_bank
    #                         resp['msg'].append('开户行修改成功')
    #                     if mobile:
    #                         bankinfo_obj.mobile = mobile
    #                         resp['msg'].append('手机修改成功')
    #                     bankinfo_obj.save()
    #                     self.perform_update(serializer)
    #                 else:
    #                     code = 400
    #                     resp['msg'].append('操作有误')
    #             else:
    #                 code = 400
    #                 resp['msg'].append('操作对象不存在')
    #
    #     else:
    #         code = 403
    #         resp['msg'].append('该用户没有操作权限')
    #     return Response(data=resp, status=code)


class GetPayView(views.APIView):
    def post(self, request):
        processed_dict = {}
        resp = {'msg': '操作成功'}
        for key, value in request.data.items():
            processed_dict[key] = value
        uid = processed_dict.get('uid', '')
        money = total_amount = processed_dict.get('total_amount', '')
        user_msg = processed_dict.get('user_msg', '')
        order_id = processed_dict.get('order_id', '')
        key = processed_dict.get('key', '')
        return_url = processed_dict.get('return_url', '')
        channel = processed_dict.get('channel', '')
        # channel=ChooseChannel(channel).make_choose()
        user_queryset = UserProfile.objects.filter(uid=uid, is_active=True)
        if not str(money) > '1':
            resp['msg'] = '金额必须大于1'
            return Response(resp, status=404)
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
        # if channel != 'atb':
        #     resp['msg'] = '请填写正确通道名称~~'
        #     return Response(resp, status=404)
        # 识别出 用户
        user = user_queryset[0]
        # 加密 uid + auth_code + total_amount + return_url + order_id
        auth_code = user.auth_code
        new_temp = str(str(uid) + str(auth_code) + str(total_amount) + str(return_url) + str(order_id))
        my_key = make_md5(new_temp)
        if key == my_key:

            bank_queryet = BankInfo.objects.filter(is_active=True, user_id=user.proxy_id).all()
            if not bank_queryet:
                resp['code'] = 404
                resp['msg'] = '收款商户未激活,或不存在有效收款卡'
                return Response(resp)

            # 关闭超时订单
            now_time = datetime.datetime.now() - datetime.timedelta(minutes=CLOSE_TIME)
            order_queryset = OrderInfo.objects.filter(pay_status='PAYING', add_time__lte=now_time).update(
                pay_status='TRADE_CLOSE')

            # # 处理金额
            while True:
                for bank in bank_queryet:
                    order_queryset = OrderInfo.objects.filter(pay_status='PAYING', total_amount=total_amount,
                                                              bank_tel=bank.bank_tel)
                    if not order_queryset:
                        account_num = bank.account_num
                        bank_tel = bank.bank_tel
                        break
                    else:
                        continue
                if order_queryset:
                    total_amount = (Decimal(total_amount) + Decimal(random.uniform(-0.9, 0.9))).quantize(
                        Decimal('0.00'))
                else:
                    break

            # channel=ChooseChannel(channel,user.id,order_no,total_amount,user_msg,order_id,bank_tel,account_num).make_choose()
            order_no = '1'
            if channel == 'atb':
                short_code = make_short_code(8)
                order_no = "{time_str}{userid}{randstr}".format(time_str=time.strftime("%Y%m%d%H%M%S"),
                                                                userid=user.id, randstr=short_code)
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
                order.money = money
                pay_url = FONT_DOMAIN + '/pay/' + order_no
                order.pay_url = pay_url
                order.receive_way = '0'
                order.save()
                resp['order_no'] = order_no
                resp['pay_url'] = pay_url
                resp['id'] = order.id
            elif channel == 'wang':
                print('total_amount', total_amount)
                order = OrderInfo()
                order.user_id = user.id
                # order.order_no = order_no
                order.pay_status = 'PAYING'
                order.total_amount = money
                order.user_msg = user_msg
                order.order_id = order_id
                order.bank_tel = bank_tel
                order.account_num = account_num
                order.money = money
                order.receive_way = '0'
                order.save()

            # 引入日志
            log = MakeLogs()
            content = '用户：' + str(user.username) + ' 创建订单_ ' + str(order_no) + '  金额 ' + str(total_amount) + ' 元'
            log.add_logs('1', content, user.id)
            resp['msg'] = '创建成功'
            resp['code'] = 200
            resp['total_amount'] = total_amount
            resp['order_id'] = order_id
            resp['add_time'] = str(order.add_time)
            resp['channel'] = channel
            resp['money'] = money
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
        print('user', user)
        if not user.is_proxy:
            print(3333333333)
            processed_dict = {}
            for key, value in self.request.data.items():
                processed_dict[key] = value
            money = processed_dict.get('total_amount', '')
            bank_tel = processed_dict.get('bank_tel', '')
            auth_code = processed_dict.get('auth_code', '')
            key = processed_dict.get('key', '')
            # orderid = processed_dict.get('id', '')
            channel = processed_dict.get('channel', '')
            order_no = processed_dict.get('order_no', '')
            print('XXXXXXXXXXXX', channel, order_no, key)
            if channel == 'atb':
                device_queryset = DeviceName.objects.filter(auth_code=auth_code, is_active=True)
                if device_queryset:
                    device_obj = device_queryset[0]
                    bank_queryset = BankInfo.objects.filter(user_id=user.id, bank_tel=bank_tel,
                                                            devices_id=device_obj.id)
                    if not bank_queryset:
                        code = 404
                        resp['msg'] = '银行卡不存在，联系管理员处理'
                        return Response(data=resp, status=code)
                    elif len(bank_queryset) == 1:
                        bank_obj = bank_queryset[0]
                        print(bank_obj.account_num)
                    else:
                        resp['msg'] = '存在多张银行卡，需手动处理'
                        code = 404
                        return Response(data=resp, status=code)

                    order_queryset = OrderInfo.objects.filter(pay_status='PAYING', total_amount=money,
                                                              account_num=bank_obj.account_num)
                    if not order_queryset:
                        code = 404
                        resp['msg'] = '订单不存在，联系管理员处理'
                        return Response(data=resp, status=code)
                    elif len(order_queryset) == 1:
                        order_obj = order_queryset[0]
                    else:
                        resp['msg'] = '存在多笔订单，需手动处理'
                        code = 404
                        return Response(data=resp, status=code)
                    # 加密顺序 money + bank_tel + auth_code + SECRET_VERIFY
                    new_temp = str(money) + str(bank_tel) + str(auth_code) + SECRET_VERIFY
                    my_key = make_md5(new_temp)

                    if key == key:
                        order_obj.pay_status = 'TRADE_SUCCESS'
                        order_obj.pay_time = datetime.datetime.now()
                        print('订单状态处理成功！！！！！！！！！！！！！！！！！！！！！！！')
                        order_obj.save()
                        user_id = order_obj.user_id
                        user_obj = UserProfile.objects.filter(id=user_id)[0]
                        account_num = order_obj.account_num
                        bank_obj = BankInfo.objects.filter(account_num=account_num)[0]

                        # 更新用户收款
                        user_obj.total_money = '%.2f' % (Decimal(user_obj.total_money) + Decimal(money))
                        user_obj.save()
                        # 代理代理收款
                        user.total_money = '%.2f' % (Decimal(user.total_money) + Decimal(money))
                        user.save()
                        # 更新商家存钱
                        bank_obj.total_money = '%.2f' % (Decimal(bank_obj.total_money) + Decimal(money))
                        bank_obj.last_time = datetime.datetime.now()
                        bank_obj.save()
                        notify_url = user_obj.notify_url

                        # 加密顺序 uid + order_no + total_amount + auth_code
                        new_temp = str(user_obj.uid) + str(order_obj.order_no) + str(order_obj.total_amount) + str(
                            auth_code)
                        my_key = make_md5(new_temp)
                        resp['key'] = my_key
                        resp['pay_status'] = order_obj.pay_status
                        resp['add_time'] = str(order_obj.add_time)
                        resp['pay_time'] = str(order_obj.pay_time)
                        resp['total_amount'] = str(order_obj.total_amount)
                        resp['order_id'] = order_obj.order_id
                        resp['order_no'] = order_obj.order_no
                        resp['user_msg'] = order_obj.user_msg
                        resp['money'] = str(order_obj.money)
                        r = json.dumps(resp)
                        headers = {'Content-Type': 'application/json'}

                        if not notify_url:
                            order_obj.pay_status = 'NOTICE_FAIL'
                            order_obj.save()
                            resp['msg'] = '订单处理成功，无效notify_url，通知失败'
                            return Response(data=resp, status=400)

                        try:
                            res = requests.post(notify_url, headers=headers, data=r, timeout=10, stream=True)
                            if res.text == 'success':
                                resp['msg'] = '订单处理成功!'
                                return Response(data=resp, status=200)
                            else:
                                order_obj.pay_status = resp['pay_status'] = 'NOTICE_FAIL'
                                order_obj.save()
                                resp['msg'] = '订单处理成功，通知失败'
                                return Response(data=resp, status=400)
                        except Exception:
                            order_obj.pay_status = resp['pay_status'] = 'NOTICE_FAIL'
                            order_obj.save()
                            print('00000000000')
                            resp['msg'] = '订单处理成功，通知失败'
                            return Response(data=resp, status=400)
                    else:
                        resp['msg'] = '加密错误'
                        code = 400
                        return Response(data=resp, status=code)
                else:
                    resp['msg'] = '设备不存在'
                    code = 400
                    return Response(data=resp, status=code)
            elif channel == 'wang' and order_no:
                # 加密顺序 money + bank_tel + auth_code + SECRET_VERIFY
                new_temp = SECRET_VERIFY + str(order_no)
                my_key = make_md5(new_temp)
                print('my_key', my_key)
                if key == my_key:
                    user_list = []
                    user_queryset = UserProfile.objects.filter(proxy_id=user.id)

                    if not user_queryset:
                        return []

                    for user_obj in user_queryset:
                        user_list.append(user_obj.id)
                    order_queryset = OrderInfo.objects.filter(order_no=order_no)
                    if order_queryset and order_queryset[0].user_id in user_list:
                        if order_queryset[0].pay_status == 'PAYING':
                            order_queryset[0].pay_status = 'TRADE_SUCCESS'
                            order_queryset[0].pay_time = datetime.datetime.now()
                            print('wang 通道 订单状态处理成功！！！！！！！！！！！！！！！！！！！！！！！')
                            order_queryset[0].save()
                            order_user = UserProfile.objects.filter(id=order_queryset[0].user_id)[0]
                            print('order_user', order_user)
                            # 更新用户收款
                            order_user.total_money = '%.2f' % (
                                        Decimal(order_user.total_money) + Decimal(order_queryset[0].total_amount))
                            order_user.save()
                            # 代理代理收款
                            user.total_money = '%.2f' % (
                                        Decimal(user.total_money) + Decimal(order_queryset[0].total_amount))
                            user.save()
                            print('66666666666')
                            # 加密顺序 uid + order_no + total_amount + auth_code
                            new_temp = str(order_user.uid) + str(order_queryset[0].order_no) + str(
                                order_queryset[0].total_amount)
                            my_key = make_md5(new_temp)
                            resp['key'] = my_key
                            resp['pay_status'] = order_queryset[0].pay_status
                            resp['add_time'] = str(order_queryset[0].add_time)
                            resp['pay_time'] = str(order_queryset[0].pay_time)
                            resp['total_amount'] = str(order_queryset[0].total_amount)
                            resp['order_id'] = order_queryset[0].order_id
                            resp['order_no'] = order_queryset[0].order_no
                            resp['user_msg'] = order_queryset[0].user_msg
                            resp['money'] = str(order_queryset[0].money)
                            r = json.dumps(resp)
                            headers = {'Content-Type': 'application/json'}
                            if not order_user.notify_url:
                                order_queryset[0].pay_status = 'NOTICE_FAIL'
                                order_queryset[0].save()
                                resp['msg'] = '订单处理成功，无效notify_url，通知失败'
                                return Response(data=resp, status=400)
                            try:
                                res = requests.post(order_user.notify_url, headers=headers, data=r, timeout=10,
                                                    stream=True)
                                if res.text == 'success':
                                    resp['msg'] = '订单处理成功!'
                                    return Response(data=resp, status=200)
                                else:
                                    order_queryset[0].pay_status = resp['pay_status'] = 'NOTICE_FAIL'
                                    order_queryset[0].save()
                                    resp['msg'] = '订单处理成功，通知失败'
                                    return Response(data=resp, status=400)
                            except Exception:
                                order_queryset[0].pay_status = resp['pay_status'] = 'NOTICE_FAIL'
                                order_queryset[0].save()
                                resp['msg'] = '订单处理成功，通知失败'
                                return Response(data=resp, status=400)
                        else:
                            resp['msg'] = '订单处理失败，非paying订单'
                            return Response(data=resp, status=400)

                    else:
                        code = 404
                        resp['msg'] = '订单不存在，联系管理员处理'
                        return Response(data=resp, status=code)
                else:
                    resp['msg'] = '加密错误'
                    code = 400
                    return Response(data=resp, status=code)
        code = 400
        resp['msg'] = '错误操作'
        return Response(data=resp, status=code)


class OrderInfoViewset(mixins.ListModelMixin, viewsets.GenericViewSet, mixins.UpdateModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    # serializer_class = VerifyPaySerializer
    serializer_class = OrderGetSerializer

    def get_queryset(self):
        user = self.request.user

        # 关闭超时订单
        now_time = datetime.datetime.now() - datetime.timedelta(minutes=CLOSE_TIME)
        OrderInfo.objects.filter(pay_status='PAYING', add_time__lte=now_time).update(
            pay_status='TRADE_CLOSE')

        if not user.is_proxy:
            user_list = []
            user_queryset = UserProfile.objects.filter(proxy_id=user.id)

            if not user_queryset:
                return []

            for user_obj in user_queryset:
                user_list.append(user_obj.id)
            return OrderInfo.objects.filter(user_id__in=user_list, pay_url__isnull=True,
                                            add_time__gte=time.strftime('%Y-%m-%d',
                                                                        time.localtime(time.time()))).order_by(
                '-add_time')
        return []

    def update(self, request, *args, **kwargs):
        user = self.request.user
        resp = {'msg': []}
        print('request.data', request.data, user)
        if not user.is_proxy:
            dict_result = request.data

            # 获取代理商户列表
            user_list = []
            user_queryset = UserProfile.objects.filter(proxy_id=user.id)
            if not user_queryset:
                resp['msg'] = '不存在有效商户'
                code = 400
                return Response(data=resp, status=code)
            for user_obj in user_queryset:
                user_list.append(user_obj.id)

            order_queryset = OrderInfo.objects.filter(id=dict_result.get('id'))
            if not dict_result.get('pay_url') or not dict_result.get('order_no'):
                resp['msg'] = '不存在有效商户'
                code = 400
                return Response(data=resp, status=code)
            if order_queryset:
                if order_queryset[0].user_id in user_list:
                    if not order_queryset[0].pay_url:
                        try:
                            print("dict_result.get('pay_url')", dict_result.get('pay_url'), dict_result.get('order_no'))
                            order_queryset[0].pay_url = dict_result.get('pay_url')
                            order_queryset[0].order_no = dict_result.get('order_no')
                            order_queryset[0].save()
                            resp['msg'] = '处理成功'
                            code = 200
                        except Exception:
                            print('00000000000')
                            resp['msg'] = '处理失败，订单号已存在'
                            return Response(data=resp, status=400)
                        return Response(data=resp, status=code)
                    else:
                        resp['msg'] = '订单已存在支付链接，请勿重复操作'
                        code = 400
                        return Response(data=resp, status=code)
                else:
                    resp['msg'] = '其他商户的订单，请勿操作'
                    code = 400
                    return Response(data=resp, status=code)
            else:
                resp['msg'] = '不存在有效订单'
                code = 400
                return Response(data=resp, status=code)
        code = 403
        resp['msg'] = '无操作权限'
        return Response(data=resp, status=code)


class WithDrawViewset(XLSXFileMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                      mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = WithDrawSerializer
    pagination_class = OrderListPagination
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filter_class = WithDrawFilter
    search_fields = ('full_name',)
    ordering_fields = ('money', 'real_money')
    renderer_classes = (renderers.JSONRenderer, XLSXRenderer, renderers.BrowsableAPIRenderer)

    column_header = {
        'titles': [
            "订单id",
            "用户名",
            "到账时间",
            "创建时间",
            "金额",
            "银行类型",
            "开户行地址",
            "提现备注",
            "收款账号",
            "收款人",
            "提现单号",
            "费率",
            "提现状态",
            "实际到账",
        ]
    }

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
        # original_safe_code = serializer.validated_data.get('original_safe_code', '')
        original_safe_code = self.request.data.get('original_safe_code', '')
        daili_queryset = UserProfile.objects.filter(id=user_up.proxy_id)
        if user_up.is_proxy or not daili_queryset:
            daili_obj = daili_queryset[0]
            if original_safe_code:
                if make_md5(original_safe_code) == self.request.user.safe_code:
                    money = serializer.validated_data.get('money', '')
                    user_money = user_up.total_money

                    if money <= user_money and daili_obj.total_money >= money:

                        instance = serializer.save()
                        withdraw_no = generate_order_no(user_up.id)
                        instance.withdraw_no = withdraw_no
                        instance.real_money = '%.2f' % (money * (1 - user_up.service_rate))
                        instance.time_rate = user_up.service_rate
                        user_up.total_money = '%.2f' % (user_money - money)

                        # 引入日志
                        log = MakeLogs()
                        content = '用户：' + str(user_up.username) + '创建提现_' + '订单号_ ' + str(withdraw_no) + '  金额 ' + str(
                            money) + ' 元'
                        log.add_logs('2', content, user_up.id)

                        user_up.save()
                        instance.save()

                        # 更新代理余额
                        daili_obj.total_money = '%.2f' % (Decimal(daili_obj.total_money) - Decimal(money))
                        daili_obj.save()
                        code = 200
                        resp['msg'] = '创建成功'
                    else:
                        code = 400
                        resp['msg'] = '金额错误，创建失败'
                    return Response(resp, status=code)
                else:
                    code = 400
                    resp['msg'] = '操作密码错误'
                return Response(resp, status=code)
            else:
                code = 400
                resp['msg'] = '请输入操作密码'
            return Response(resp, status=code)
        code = 400
        resp['msg'] = '创建失败'
        return Response(data=resp, status=code)

    def update(self, request, *args, **kwargs):
        resp = {'msg': []}
        withdraw_obj = self.get_object()
        code = 200
        if not self.request.user.is_proxy:
            withdraw_status = str(self.request.data.get('withdraw_status', ''))
            remark_info = (self.request.data.get('remark_info', ''))
            print('withdraw_status', withdraw_status)
            if withdraw_status == '1' and withdraw_obj.withdraw_status == '0':
                withdraw_obj.withdraw_status = withdraw_status
                withdraw_obj.receive_time = resp['receive_time'] = (
                    time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time())))
                code = 200
                resp['msg'].append('状态修改成功')

                # 引入日志
                log = MakeLogs()
                content = '用户：' + str(self.request.user.username) + ' 处理提现_' + '订单号_ ' + str(
                    withdraw_obj.withdraw_no) + ' 状态为_ 提现成功'
                log.add_logs('2', content, self.request.user.id)

            elif withdraw_status == '2' and withdraw_obj.withdraw_status == '0':
                user_queryset = UserProfile.objects.filter(id=withdraw_obj.user_id)
                if user_queryset:
                    user = user_queryset[0]
                    daili_queryset = UserProfile.objects.filter(id=user.proxy_id)
                    if daili_queryset:
                        daili_obj = daili_queryset[0]
                        user.total_money = '%.2f' % (user.total_money + withdraw_obj.money)

                        # 更新代理余额
                        daili_obj.total_money = '%.2f' % (Decimal(daili_obj.total_money) + Decimal(withdraw_obj.money))
                        daili_obj.save()

                        code = 200
                        resp['msg'].append('状态修改成功')
                        user.save()
                        withdraw_obj.withdraw_status = withdraw_status

                        # 引入日志
                        log = MakeLogs()
                        content = '用户：' + str(self.request.user.username) + ' 处理提现_' + '订单号_ ' + str(
                            withdraw_obj.withdraw_no) + ' 状态为_ 提现驳回'
                        log.add_logs('2', content, self.request.user.id)
                    else:
                        code = 400
                        resp['msg'].append('余额处理失败，代理不存在')
                else:
                    code = 400
                    resp['msg'].append('用户不存在')
            # else:
            #     code = 400
            #     resp['msg'].append('操作有误')
            if remark_info:
                print('remark_info', remark_info)
                if str(remark_info) == '1':
                    withdraw_obj.remark_info = ''
                else:
                    withdraw_obj.remark_info = remark_info
                code = 200
                resp['msg'].append('备注修改成功')
            withdraw_obj.save()
        else:
            code = 403
            resp['msg'].append('该用户没有操作权限')
        return Response(data=resp, status=code)


import base64
import qrcode


def pay(request):
    order_id = request.GET.get('id')
    if order_id:

        # 关闭超时订单
        now_time = datetime.datetime.now() - datetime.timedelta(minutes=CLOSE_TIME)
        OrderInfo.objects.filter(pay_status='PAYING', add_time__lte=now_time).update(
            pay_status='TRADE_CLOSE')

        order_queryset = OrderInfo.objects.filter(order_no=order_id, pay_status='PAYING')
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
            # print('pay_url', base64_data)
            a = (b'data:image/png;base64,' + (base64_data)).decode('utf-8')
            return render(request, 'pay.html', {
                "pay_url": a
            })
        else:
            return HttpResponse('订单失效')
    else:
        return HttpResponse('链接错误')


def mobile_pay(request):
    order_id = request.GET.get('id')
    print('order_id', order_id)
    resp = {}
    if order_id:

        # 关闭超时订单
        now_time = datetime.datetime.now() - datetime.timedelta(minutes=CLOSE_TIME)
        OrderInfo.objects.filter(pay_status='PAYING', add_time__lte=now_time).update(
            pay_status='TRADE_CLOSE')

        order_queryset = OrderInfo.objects.filter(pay_status='PAYING', order_no=order_id)
        if order_queryset:
            print(2)
            order_obj = order_queryset[0]
            account_num = order_obj.account_num
            bank_qset = BankInfo.objects.filter(account_num=account_num)
            if bank_qset:
                print(1)
                bank_obj = bank_qset[0]
                resp['msg'] = '操作成功'
                resp['money'] = order_obj.total_amount
                resp['card_index'] = bank_obj.card_index
                resp['name'] = bank_obj.name
                resp['bank_mark'] = bank_obj.bank_mark
                return JsonResponse(data=resp, status=200)
            else:
                resp['msg'] = '银行卡不存在'
                return JsonResponse(data=resp, status=400)

        else:
            resp['msg'] = '订单不存在'
            return JsonResponse(data=resp, status=400)

    else:
        resp['msg'] = '订单不存在'
        return JsonResponse(data=resp, status=400)


class DevicesViewset(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet, mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = DeviceSerializer
    pagination_class = OrderListPagination
    '状态,时间范围，金额范围'

    filter_backends = (DjangoFilterBackend,)
    filter_class = DeviceFilter

    # throttle_classes = [MyThrottle, ]
    def get_serializer_class(self):
        if self.action == "create":
            return RegisterDeviceSerializer
        elif self.action == "update":
            return UpdateDeviceSerializer
        return DeviceSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return DeviceName.objects.all().order_by('-add_time')
        user = self.request.user
        if not user.is_proxy:
            return DeviceName.objects.filter(user=user).order_by('-add_time')
        return []

    def create(self, request, *args, **kwargs):
        resp = {'msg': []}
        if self.request.user.is_superuser:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            get_userid = self.request.data.get('id', '')
            if not get_userid:
                code = 400
                resp['msg'] = 'id不符，创建失败'
                return Response(resp, status=code)
            is_active = serializer.validated_data.get('is_active', 'False')
            user_queryset = UserProfile.objects.filter(id=get_userid, is_proxy=False)
            if user_queryset:
                instance = serializer.save()
                instance.user_id = user_queryset[0].id
                instance.auth_code = make_auth_code()
                instance.login_token = make_login_token()
                instance.is_active = is_active
                instance.save()
                code = 200
                resp['msg'] = '创建成功'
                return Response(resp, status=code)
            else:
                code = 400
                resp['msg'] = 'id不符，创建失败'
                return Response(resp, status=code)
        elif not self.request.user.is_proxy:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            is_active = serializer.validated_data.get('is_active', 'False')
            instance = serializer.save()
            instance.auth_code = make_auth_code()
            instance.login_token = make_login_token()
            instance.is_active = is_active
            instance.save()
            code = 200
            resp['msg'] = '创建成功'
            return Response(resp, status=code)
        code = 403
        resp['msg'] = '没有权限'
        return Response(resp, status=code)

    # def update(self, request, *args, **kwargs):
    #     resp = {'msg': []}
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     # obj = self.get_object()
    #     code = 200
    #     if not self.request.user.is_proxy:
    #         is_active = self.request.data.get('is_active', '')
    #         auth_code = self.request.data.get('auth_code', '')
    #         login_token = self.request.data.get('login_token', '')
    #         username = self.request.data.get('username', '')
    #         get_deviceid = self.request.data.get('id', '')
    #         # tuoxie 修改 tuoxie001
    #         if not self.request.user.is_proxy:
    #             id_list = [device_obj.id for device_obj in DeviceName.objects.filter(user_id=self.request.user.id)]
    #             if get_deviceid:
    #                 if int(get_deviceid) in id_list:
    #                     device_obj=DeviceName.objects.get(id=get_deviceid)
    #                     if is_active:
    #                         if is_active == 'true':
    #                             is_active = True
    #                         if is_active == 'false':
    #                             is_active = False
    #                         device_obj.is_active = is_active
    #                         resp['msg'].append('状态修改成功')
    #                     if auth_code:
    #                         device_obj.auth_code = make_auth_code()
    #                         resp['msg'].append('授权码修改成功')
    #                     if login_token:
    #                         device_obj.login_token = make_login_token()
    #                         resp['msg'].append('登录码修改成功')
    #                     if username:
    #                         device_obj.username = username
    #                         resp['msg'].append('用户名修改成功')
    #                     device_obj.save()
    #                 else:
    #                     code = 400
    #                     resp['msg'].append('操作有误')
    #
    #     else:
    #         code = 403
    #         resp['msg'].append('该用户没有操作权限')
    #     return Response(data=resp, status=code)


# def export_csv(request):
#     dataset = SchoolResource().export()
#     a = dataset.csv
#     return HttpResponse(str(a))


from django.http import HttpResponse
from django.template import loader, Context

import csv

from django.http import StreamingHttpResponse


def export_csv(request):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="test.csv"'

    writer = csv.writer(response)
    writer.writerow(['First row', 'Foo', 'Bar', 'Baz'])
    writer.writerow(['Second row', 'A', 'B', 'C', '"Testing"', "Here's a quote"])
    writer.writerow(['Second row', 'A', 'B', 'C', '"Testing"', "Here's a quote"])
    writer.writerow(['Second row', 'A', 'B', 'C', '"Testing"', "Here's a quote"])

    return response


class ExportViewset(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    queryset = OrderInfo.objects.all()
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = VerifyPaySerializer

    def list(self, request, *args, **kwargs):
        user = self.request.user
        resp = {'msg': '操作成功'}
        print('user', user)
        if not user.is_proxy:
            print('tuoxie导出操作')
            processed_dict = {}
            for key, value in self.request.data.items():
                processed_dict[key] = value
            money = processed_dict.get('total_amount', '')
            key = processed_dict.get('key', '')
            # if key == 'key':
            print('money', money)
            user_list = []
            user_queryset = UserProfile.objects.filter(proxy_id=user.id)

            if not user_queryset:
                return OrderInfo.objects.filter(user=self.request.user).order_by('-add_time')

            for user_obj in user_queryset:
                user_list.append(user_obj.id)
            order_queryset = OrderInfo.objects.filter(Q(user_id__in=user_list) | Q(user=self.request.user)).order_by(
                '-add_time')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="test.csv"'

            writer = csv.writer(response)
            writer.writerow(['用户名', '订单时间', '付款时间', '订单编号', '支付状态'])

            for order in order_queryset:
                a = []
                a.append(order.user_id)
                a.append(order.add_time)
                a.append(order.pay_time)
                a.append(order.order_no)
                a.append(order.pay_status)
                writer.writerow(a)

            return response
        elif user.is_proxy:

            return None

        code = 403
        resp['msg'] = '无操作权限'
        return Response(data=resp, status=code)


class QueryOrderView(views.APIView):
    def post(self, request):
        processed_dict = {}
        resp = {'msg': '订单不存在', 'code': 400}
        for key, value in request.data.items():
            processed_dict[key] = value
        uid = processed_dict.get('uid', '')
        order_no = processed_dict.get('order_no', '')
        user_queryset = UserProfile.objects.filter(uid=uid, is_active=True)
        if user_queryset:
            user = user_queryset[0]
            order_queryset = OrderInfo.objects.filter(user=user, order_no=order_no)
            if order_queryset:
                order = order_queryset[0]
                resp['msg'] = '查询成功'
                resp['code'] = 200
                resp['total_amount'] = order.total_amount
                resp['usr_msg'] = order.user_msg
                resp['add_time'] = order.add_time
                resp['pay_status'] = order.pay_status
                resp['order_no'] = order.order_no
                resp['order_id'] = order.order_id
                resp['pay_time'] = order.pay_time
                resp['pay_url'] = order.pay_url
                resp['money'] = order.money
                resp['channel'] = eval('order.get_receive_way_display()')  # eval('obj.get_receive_way_display()')
                return Response(resp)
        return Response(resp)


class ReleaseViewset(mixins.DestroyModelMixin, viewsets.GenericViewSet, mixins.ListModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = ReleaseSerializer
    pagination_class = OrderListPagination

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        return []

    def destroy(self, request, *args, **kwargs):
        user = self.request.user
        resp = {'msg': '操作成功'}
        if user.is_superuser:
            processed_dict = {}
            for key, value in self.request.data.items():
                processed_dict[key] = value
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            s_time = serializer.validated_data.get('s_time', '')
            e_time = serializer.validated_data.get('e_time', '')
            dele_type = serializer.validated_data.get('dele_type', '')
            safe_code = serializer.validated_data.get('safe_code', '')
            new_key = make_md5(safe_code)
            if new_key == user.safe_code:
                if dele_type == 'order':
                    order_queryset = OrderInfo.objects.filter(add_time__range=(s_time, e_time))
                elif dele_type == 'money':
                    order_queryset = WithDrawMoney.objects.filter(add_time__range=(s_time, e_time))
                elif dele_type == 'log':
                    order_queryset = OperateLog.objects.filter(add_time__range=(s_time, e_time))
                else:
                    code = 400
                    resp['msg'] = '类型错误'
                    return Response(data=resp, status=code)
                if order_queryset:
                    for obj in order_queryset:
                        print(obj.id)
                        obj.delete()
                code = 200
                return Response(data=resp, status=code)
            else:
                code = 400
                resp['msg'] = '操作密码错误'
                return Response(data=resp, status=code)
        else:
            code = 403
            resp['msg'] = '没有权限'
            return Response(data=resp, status=code)


@csrf_exempt
def test(request):
    print('接收到的信息', request.body)
    return HttpResponse('Success')


def get_info(request):
    order_id = request.GET.get('id')
    resp = {'msg': []}
    if order_id:
        order_queryset = OrderInfo.objects.filter(id=order_id)
        code = 200
        if order_queryset:
            print(order_queryset.query)
            resp['msg'] = '获取成功'
            resp['money'] = order_queryset[0].money
            resp['pay_url'] = order_queryset[0].pay_url
        else:
            resp['msg'] = '不存在相应订单号'
            code = 400
    else:
        resp['msg'] = '不存在相应订单号'
        code = 400
    return JsonResponse(data=resp, status=code)
