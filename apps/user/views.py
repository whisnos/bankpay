import json, time
from decimal import Decimal
import datetime
import requests
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status

# Create your views here.
from rest_framework.authentication import SessionAuthentication
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from trade.filters import LogFilter
from trade.models import OrderInfo
from trade.serializers import OrderListSerializer, OrderSerializer, OrderUpdateSeralizer
from trade.views import OrderListPagination
from user.filters import UserFilter
from user.models import UserProfile, DeviceName, NoticeInfo, VersionInfo, OperateLog, BankInfo
from user.serializers import RegisterUserSerializer, UserDetailSerializer, UpdateUserSerializer, NoticeInfoSerializer, \
    LogInfoSerializer, LogListInfoSerializer
from django.contrib.auth import get_user_model

from utils.make_code import make_uuid_code, make_auth_code, make_md5
from utils.permissions import IsOwnerOrReadOnly, MakeLogs

User = get_user_model()


def log_in(func):
    def wrapper(request, *args, **kwargs):
        print('request.data', request.POST.get("type"))
        if not request.POST.get("type"):
            #
            return func(request, *args, **kwargs)
        return func(request, *args, **kwargs)

    return wrapper


# @log_in
class CustomModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, type=None, **kwargs):
        user = User.objects.filter(username=username).first() or DeviceName.objects.filter(username=username).first()
        try:
            if user.level:
                if user.check_password(password):

                    return user
                else:
                    print(666)
                    return None
        except Exception as e:
            try:
                if user.login_token == password:
                    userid = user.user_id
                    user = User.objects.get(id=userid)
                    return user
                return None
            except Exception as e:
                return None


class UserListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100


VISIT_RECORD = {}


# 自定义限制
class MyThrottle(object):

    def __init__(self):
        self.history = None

    def allow_request(self, request, view):
        """
        自定义频率限制60秒内只能访问三次
        """
        # 获取用户IP
        ip = request.META.get("REMOTE_ADDR")
        print('获取访问者ip....', ip)
        timestamp = time.time()
        if ip not in VISIT_RECORD:
            VISIT_RECORD[ip] = [timestamp, ]
            return True
        history = VISIT_RECORD[ip]
        self.history = history
        history.insert(0, timestamp)
        while history and history[-1] < timestamp - 60:
            history.pop()
        if len(history) > 3:
            return False
        else:
            return True

    def wait(self):
        """
        限制时间还剩多少
        """
        timestamp = time.time()
        return 60 - (timestamp - self.history[-1])


class UserProfileViewset(mixins.ListModelMixin, viewsets.GenericViewSet, mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin, mixins.DestroyModelMixin):
    '''
        total_money: 总成功收款 ---
        total_count_num: 总订单数 - 包括支付中 ---
        total_count_success_num: 总成功订单数 ---
        total_count_fail_num: 总失败订单数 ---
        total_count_paying_num: 总未支付订单数 ---
        today_receive_all: 今日总收款 包括成功与否 ---
        today_count_num: 今日总订单数 所有 包括成功与否 ---
        today_count_success_num: 今日订单数(仅含成功订单)
    '''
    # queryset = UserProfile.objects.all()
    # serializer_class = RegisterUserSerializer
    pagination_class = UserListPagination
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    filter_backends = (DjangoFilterBackend,)
    filter_class = UserFilter

    # throttle_classes = [MyThrottle, ]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return UserProfile.objects.all().order_by('id')  # .exclude(id=user.id)
        return UserProfile.objects.filter(proxy_id=user.id).order_by('id')

    def get_serializer_class(self):
        # if self.action == "retrieve":
        #     return UserDetailSerializer
        if self.action == "create":
            return RegisterUserSerializer
        # elif self.action == "list":
        #     return UserDetailSerializer
        elif self.action == "update":
            return UpdateUserSerializer
        return UserDetailSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        elif self.action == "create":
            return [IsAuthenticated()]
        elif self.action == "list":
            return [IsAuthenticated()]
        else:
            return []

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        resp = {'msg': []}
        if self.request.user.is_superuser:
            get_proxyid = self.request.data.get('id')
            user_queryset = UserProfile.objects.filter(id=get_proxyid)
            if user_queryset:
                instance = user_queryset[0]
                code = 200
                resp['msg'] = '删除成功'
                self.perform_destroy(instance)
                return Response(data=resp, status=code)
            else:
                code = 400
                resp['msg'] = '操作对象不存在'
                return Response(data=resp, status=code)
        else:
            code = 403
            resp['msg'] = '没有操作权限'
            return Response(data=resp, status=code)

    def update(self, request, *args, **kwargs):
        resp = {'msg': []}
        code = 200
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = self.request.data.get('password', '')
        password2 = self.request.data.get('password2', '')
        notify_url = self.request.data.get('notify_url', '')
        get_proxyid = self.request.data.get('id', '')
        add_money = self.request.data.get('add_money', '')
        minus_money = self.request.data.get('minus_money', '')
        auth_code = self.request.data.get('auth_code', '')
        is_active = self.request.data.get('is_active', '')
        original_safe_code = self.request.data.get('original_safe_code', '')
        safe_code = self.request.data.get('safe_code', '')
        safe_code2 = self.request.data.get('safe_code2', '')
        proxy_id = self.request.data.get('proxy_id', '')
        service_rate = self.request.data.get('service_rate', '')

        print('self.request.user', self.request.user)
        if self.request.user.is_superuser:
            if get_proxyid:
                user_queryset = UserProfile.objects.filter(id=get_proxyid)
                if user_queryset:
                    # 引入日志
                    log = MakeLogs()
                    user = user_queryset[0]

                    if add_money:
                        user.total_money = '%.2f' % (Decimal(user.total_money) + Decimal(add_money))
                        resp['msg'].append('加款成功')
                        # 加日志
                        content = '用户：' + str(self.request.user.username) + ' 对 ' + str(
                            user.username) + ' 加款 ' + ' 金额_' + str(add_money)
                        log.add_logs('3', content, self.request.user.id)
                    if minus_money:
                        if Decimal(minus_money) < Decimal(user.total_money):
                            user.total_money = '%.2f' % (Decimal(user.total_money) - Decimal(minus_money))
                            resp['msg'].append('扣款成功')
                            # 加日志
                            content = '用户：' + str(self.request.user.username) + ' 对 ' + str(
                                user.username) + ' 扣款 ' + ' 金额_' + str(add_money)
                            log.add_logs('3', content, self.request.user.id)
                        else:
                            # code = 404
                            resp['msg'].append('余额不足，扣款失败')

                    if password == password2:
                        if password:
                            user.set_password(password)
                            resp['msg'].append('密码修改成功')

                            # 加日志
                            content = '用户：' + str(self.request.user.username) + ' 对 ' + str(user.username) + '修改密码'
                            log.add_logs('3', content, self.request.user.id)
                    else:
                        resp['msg'].append('输入密码不一致')

                    if safe_code == safe_code2:
                        if password:
                            print('admin修改用户操作密码中..........')
                            user.safe_code = make_md5(safe_code)
                            resp['msg'].append('操作密码修改成功')
                    else:
                        resp['msg'].append('操作输入密码不一致')

                    if str(is_active):
                        if is_active == 'true':
                            is_active = True
                        if is_active == 'false':
                            is_active = False
                        resp['msg'].append('用户状态修改成功')
                        user.is_active = is_active

                    if service_rate:
                        resp['msg'].append('费率修改成功')
                        old_c = user.service_rate

                        user.service_rate = float(service_rate)
                        # 加日志
                        content = '用户：' + str(self.request.user.username) + ' 对 ' + str(user.username) + ' 原费率_' + str(
                            old_c) + ' 改为_' + str(service_rate)
                        log.add_logs('3', content, self.request.user.id)

                    if proxy_id:
                        user_proxy = UserProfile.objects.filter(id=proxy_id, is_proxy=False, is_active=True)
                        if user_proxy:
                            new_user = user_proxy[0]
                            new_c = new_user.username

                            old_c = user.username
                            old_user = UserProfile.objects.filter(id=user.proxy_id)
                            if old_user:
                                old_user_name = old_user[0].username
                            else:
                                old_user_name = ''
                            user.proxy_id = proxy_id
                            resp['msg'].append('商户调整成功')
                            user.save()
                            serializer = UserDetailSerializer(user)
                            resp['data'] = serializer.data

                            content = '商户调整：' + str(old_c) + '属：' + str(old_user_name) + ' 调整给：' + str(new_c)
                            log.add_logs('3', content, self.request.user.id)

                        else:
                            resp['msg'].append('调整失败，代理不存在')

                    code = 200
                    user.save()

                else:
                    code = 404
                    resp['msg'].append('操作对象不存在')
            else:
                if password == password2:
                    if password:
                        print('admin修改密码中..........')
                        self.request.user.set_password(password)
                        code = 200
                        resp['msg'].append('密码修改成功')
                        self.request.user.save()
                else:
                    code = 404
                    resp['msg'].append('输入密码不一致')

                if original_safe_code:
                    if make_md5(original_safe_code) == self.request.user.safe_code:
                        if safe_code == safe_code2:
                            if safe_code:
                                print('admin修改操作密码中..........')
                                safe_code = make_md5(safe_code)
                                self.request.user.safe_code = safe_code
                                code = 200
                                resp['msg'].append('操作密码修改成功')
                                self.request.user.save()
                        else:
                            code = 404
                            resp['msg'].append('操作密码输入不一致')

                    else:
                        code = 404
                        resp['msg'].append('操作密码错误')
                else:
                    code = 404
                    resp['msg'].append('操作密码错误1')

        # tuoxie 修改 tuoxie001
        if not self.request.user.is_proxy and not self.request.user.is_superuser:
            id_list = [user_obj.id for user_obj in UserProfile.objects.filter(proxy_id=self.request.user.id)]
            if get_proxyid:
                if int(get_proxyid) in id_list:
                    user = UserProfile.objects.filter(id=get_proxyid)[0]
                    # 引入日志
                    log = MakeLogs()
                    if add_money:
                        user.total_money = '%.2f' % (Decimal(user.total_money) + Decimal(add_money))
                        resp['msg'].append('加款成功')
                        # 加日志
                        content = '用户：' + str(self.request.user.username) + ' 对 ' + str(
                            user.username) + ' 加款 ' + ' 金额_' + str(add_money)
                        log.add_logs('3', content, self.request.user.id)
                    if minus_money:
                        if Decimal(minus_money) < Decimal(user.total_money):
                            user.total_money = '%.2f' % (Decimal(user.total_money) - Decimal(minus_money))
                            resp['msg'].append('扣款成功')
                            # 加日志
                            content = '用户：' + str(self.request.user.username) + ' 对 ' + str(
                                user.username) + ' 扣款 ' + ' 金额_' + str(add_money)
                            log.add_logs('3', content, self.request.user.id)
                        else:
                            # code = 404
                            resp['msg'].append('余额不足，扣款失败')

                    if password == password2:
                        if password:
                            user.set_password(password)
                            resp['msg'].append('密码修改成功')

                            # 加日志
                            content = '用户：' + str(self.request.user.username) + ' 对 ' + str(user.username) + '修改密码'
                            log.add_logs('3', content, self.request.user.id)
                    else:
                        # code = 404
                        resp['msg'].append('输入密码不一致')

                    if notify_url:
                        user.notify_url = notify_url
                        resp['msg'].append('回调修改成功')

                    if auth_code:
                        user.auth_code = make_auth_code()
                        resp['msg'].append('秘钥修改成功')
                        resp['auth_code'] = user.auth_code
                        # resp['auth_code'].append(str(user.auth_code))
                    if str(is_active):
                        if is_active == 'true':
                            is_active = True
                        if is_active == 'false':
                            is_active = False
                        resp['msg'].append('用户状态修改成功')
                        user.is_active = is_active
                    if service_rate:
                        resp['msg'].append('费率修改成功')
                        old_c = user.service_rate
                        user.service_rate = float(service_rate)

                        # 加日志
                        content = '用户：' + str(self.request.user.username) + ' 对 ' + str(user.username) + ' 原费率_' + str(
                            old_c) + ' 改为_' + str(service_rate)
                        log.add_logs('3', content, self.request.user.id)
                    if safe_code == safe_code2:
                        if password:
                            print('代理修改商户操作密码中..........')
                            self.request.user.safe_code = make_md5(safe_code)
                            resp['msg'].append('操作密码修改成功')
                    else:
                        # code = 404
                        resp['msg'].append('操作输入密码不一致')
                    code = 200
                    user.save()
                else:
                    code = 404
                    resp['msg'].append('修改代理号不存在')

        # 修改tuoxie本身数据
        if not get_proxyid and not self.request.user.is_proxy:
            qq = self.request.data.get('qq', '')
            user = self.request.user

            # if add_money:
            #     user.total_money = '%.2f' % (Decimal(user.total_money) + Decimal(add_money))
            #     resp['msg'].append('加款成功')
            # if minus_money:
            #     if Decimal(minus_money) < Decimal(user.total_money):
            #         user.total_money = '%.2f' % (Decimal(user.total_money) - Decimal(minus_money))
            #         resp['msg'].append('扣款成功')
            #     else:
            #         code = 404
            #         resp['msg'].append('余额不足，扣款失败')

            if password == password2:
                if password:
                    user.set_password(password)
                    resp['msg'].append('密码修改成功')
            else:
                code = 404
                resp['msg'].append('输入密码不一致')

            if notify_url:
                user.notify_url = notify_url
                resp['msg'].append('回调修改成功')
            if qq:
                user.qq = qq

            if auth_code:
                user.auth_code = make_auth_code()
                resp['msg'].append(user.auth_code)

            if service_rate:
                resp['msg'].append('费率修改成功')
                user.service_rate = service_rate
            user.save()

        # tuoxie001 修改自己
        if self.request.user.is_proxy:
            user = self.get_object()
            if password:
                if password == password2:
                    user.set_password(password)
                    resp['msg'].append('密码修改成功')
                elif password != password2:
                    code = 404
                    resp['msg'].append('输入密码不一致')
                else:
                    code = 403
                    resp['msg'].append('改账号无权限')
            if notify_url:
                user.notify_url = notify_url
                resp['msg'].append('回调修改成功')
            if auth_code:
                user.auth_code = make_auth_code()
                resp['msg'].append(user.auth_code)

            if service_rate:
                resp['msg'].append('费率修改失败')

            if original_safe_code:
                if make_md5(original_safe_code) == self.request.user.safe_code:
                    if safe_code == safe_code2:
                        if safe_code:
                            print('admin修改操作密码中..........')
                            safe_code = make_md5(safe_code)
                            self.request.user.safe_code = safe_code

                            resp['msg'].append('操作密码修改成功')
                    else:
                        code = 404
                        resp['msg'].append('操作密码输入不一致')

                else:
                    code = 404
                    resp['msg'].append('操作密码错误')
            user.save()
        return Response(data=resp, status=code)


@csrf_exempt
def device_login(request):
    resp = {'msg': '操作成功'}
    if request.method == 'POST':
        result = request.body
        try:
            dict_result = json.loads(result)
        except Exception:
            code = 400
            resp['msg'] = '请求方式错误,请用json格式传参'
            return JsonResponse(resp, status=code)
        username = dict_result.get('username')
        login_token = dict_result.get('login_token')
        device_queryset = DeviceName.objects.filter(username=username)
        if not device_queryset:
            code = 400
            resp['msg'] = '登录失败'
            return JsonResponse(resp, status=code)
        device_obj = device_queryset[0]
        if device_obj.login_token != login_token:
            code = 400
            resp['msg'] = '登录失败'
            return JsonResponse(resp, status=code)
        auth_code = device_obj.auth_code
        code = 200
        resp['auth_code'] = auth_code
        return JsonResponse(resp, status=code)
    else:
        code = 400
        resp['msg'] = '仅支持POST'
        return JsonResponse(resp, status=code)


class NoticeInfoViewset(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                        mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin):
    serializer_class = NoticeInfoSerializer
    queryset = NoticeInfo.objects.all().order_by('-add_time')
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    pagination_class = UserListPagination
    filter_backends = (SearchFilter,)
    search_fields = ('title', "content")

    def get_permissions(self):
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        elif self.action == "create":
            return [IsAuthenticated()]
        elif self.action == "list":
            return [IsAuthenticated()]
        else:
            return []

    def create(self, request, *args, **kwargs):
        if self.request.user.is_superuser:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            code = 201
            self.perform_create(serializer)
            response_data = {'msg': '创建成功'}
            headers = self.get_success_headers(response_data)
            return Response(response_data, status=code, headers=headers)

        code = 403
        response_data = {'msg': '没有权限'}
        headers = self.get_success_headers(response_data)
        return Response(response_data, status=code, headers=headers)


class ChartInfoViewset(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    serializer_class = OrderListSerializer
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def make_userid_list(self, obj):
        userid_list = []
        if not obj.is_proxy and not obj.is_superuser:
            user_qset = UserProfile.objects.filter(proxy_id=obj.id)
            for user in user_qset:
                userid_list.append(user.id)
        elif obj.is_proxy:
            userid_list.append(obj.id)
        elif obj.is_superuser:
            user_qset = UserProfile.objects.filter(is_proxy=True)
            for user in user_qset:
                userid_list.append(user.id)
        return userid_list

    def get_permissions(self):
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        elif self.action == "create":
            return [IsAuthenticated()]
        elif self.action == "list":
            return [IsAuthenticated()]
        else:
            return []

    def get_queryset(self):
        user = self.request.user
        print('user', user)
        userid_list = self.make_userid_list(user)
        if user:
            today_time = time.strftime('%Y-%m-%d', time.localtime())
            return OrderInfo.objects.filter(
                Q(pay_status__icontains='TRADE_SUCCESS') | Q(pay_status__icontains='NOTICE_FAIL'),
                user_id__in=userid_list, add_time__gte=today_time,
            ).order_by('-add_time')
        return []


def version(request):
    resp = {}
    ver_obj = VersionInfo.objects.all().last()
    if not ver_obj:
        resp['msg'] = '获取失败'
        return JsonResponse(resp, status=400)
    resp['msg'] = '获取成功'
    resp['vs'] = ver_obj.version_no
    resp['link'] = ver_obj.update_link
    resp['remark'] = ver_obj.remark
    return JsonResponse(resp)


class LogsViewset(viewsets.GenericViewSet, mixins.ListModelMixin):
    serializer_class = LogInfoSerializer
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    pagination_class = UserListPagination
    # filter_backends = (SearchFilter,)
    # search_fields = ("content")
    filter_backends = (DjangoFilterBackend,)
    filter_class = LogFilter

    def get_queryset(self):
        if self.request.user.is_proxy:
            return OperateLog.objects.filter(user_id=self.request.user.id).order_by('-id')
        if self.request.user.is_superuser:
            return OperateLog.objects.all().order_by('-id')
        if not self.request.user.is_proxy:
            return OperateLog.objects.filter(user_id=self.request.user.id).order_by('-id')

    def get_permissions(self):
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        elif self.action == "create":
            return [IsAuthenticated()]
        elif self.action == "list":
            return [IsAuthenticated()]
        else:
            return []

    def get_serializer_class(self):
        if self.action == 'list':
            return LogListInfoSerializer
        else:
            return LogInfoSerializer
    # def create(self, request, *args, **kwargs):
    #     if self.request.user.is_superuser:
    #         serializer = self.get_serializer(data=request.data)
    #         serializer.is_valid(raise_exception=True)
    #         code = 201
    #         self.perform_create(serializer)
    #         response_data = {'msg': '创建成功'}
    #         headers = self.get_success_headers(response_data)
    #         return Response(response_data, status=code, headers=headers)
    #
    #     code = 403
    #     response_data = {'msg': '没有权限'}
    #     headers = self.get_success_headers(response_data)
    #     return Response(response_data, status=code, headers=headers)


class CallBackViewset(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.UpdateModelMixin):
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    # serializer_class = OrderListSerializer
    pagination_class = OrderListPagination

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_serializer_class(self):
        # if self.action == "create":
        #     return OrderSerializer
        if self.action == "update":
            return OrderUpdateSeralizer
        return OrderListSerializer

    def get_queryset(self):
        if self.request.user.is_proxy:
            return []
        if self.request.user.is_superuser:
            return OrderInfo.objects.all().order_by('-id')
        if not self.request.user.is_proxy:
            userid_list = []
            user_qset = UserProfile.objects.filter(proxy_id=self.request.user.id)
            for user in user_qset:
                userid_list.append(user.id)
            return OrderInfo.objects.filter(user_id__in=userid_list)

    def update(self, request, *args, **kwargs):
        user = self.request.user
        resp = {'msg': []}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        userid_list = []
        user_qset = UserProfile.objects.filter(proxy_id=self.request.user.id)
        for users in user_qset:
            userid_list.append(users.id)
        id = self.request.data.get('id', '')
        order_queryset = OrderInfo.objects.filter(id=id)
        if order_queryset:
            order_obj=order_queryset[0]
            id = order_obj.user_id
        else:
            resp['msg'] = '订单不存在'
            return Response(data=resp, status=400)
        if user.is_superuser:
            id = '1'
            userid_list = ['1']
        if id in userid_list:
            # order_obj = self.get_object()
            if user.is_superuser or not user.is_proxy:
                if order_obj.pay_status in ['NOTICE_FAIL', 'TRADE_CLOSE']:
                    user_queryset = UserProfile.objects.filter(id=order_obj.user_id)
                    if user_queryset:
                        order_user = user_queryset[0]
                        notify_url = order_user.notify_url
                        if not notify_url:
                            order_obj.pay_status = 'NOTICE_FAIL'
                            order_obj.save()
                            resp['msg'] = '订单处理成功，无效notify_url，通知失败'
                            return Response(data=resp, status=400)

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

                        if order_obj.pay_status == 'NOTICE_FAIL':
                            try:
                                res = requests.post(notify_url, headers=headers, data=r, timeout=10, stream=True)
                                if res.text == 'success':
                                    resp['msg'] = '回调成功，成功更改订单状态!'
                                    order_obj.pay_status = 'TRADE_SUCCESS'
                                    order_obj.save()
                                    return Response(data=resp, status=200)
                                else:
                                    resp['msg'] = '回调处理，未修改状态，通知失败'
                                    return Response(data=resp, status=200)
                            except Exception:
                                resp['msg'] = '回调异常，订单状态未失败'
                                return Response(data=resp, status=400)
                        if order_obj.pay_status == 'TRADE_CLOSE':
                            try:
                                res = requests.post(notify_url, headers=headers, data=r, timeout=10, stream=True)
                                if res.text == 'success':

                                    # 更新用户收款
                                    order_user.total_money = '%.2f' % (
                                            Decimal(order_user.total_money) + Decimal(order_obj.total_amount))
                                    order_user.save()

                                    account_num = order_obj.account_num
                                    bank_queryset = BankInfo.objects.filter(account_num=account_num)
                                    if bank_queryset:
                                        bank_obj = bank_queryset[0]

                                        # 更新商家存钱
                                        bank_obj.total_money = '%.2f' % (
                                                Decimal(bank_obj.total_money) + Decimal(order_obj.total_amount))
                                        bank_obj.last_time = datetime.datetime.now()
                                        bank_obj.save()

                                    else:
                                        resp['mark'] = '不存在有效银行卡，金额未添加到银行卡'
                                    resp['data']['pay_status']='TRADE_SUCCESS'
                                    resp['data']['pay_time'] = datetime.datetime.now()
                                    order_obj.pay_status = 'TRADE_SUCCESS'
                                    order_obj.save()
                                    resp['msg'] = '回调成功，已自动加款，金额:' + str(order_obj.total_amount)
                                    return Response(data=resp, status=200)
                                else:
                                    resp['msg'] = '回调处理完成，一样通知失败'
                                    return Response(data=resp, status=400)
                            except Exception:
                                order_obj.pay_status = 'NOTICE_FAIL'
                                order_obj.save()
                                resp['msg'] = '回调处理，通知失败，未加款'
                                return Response(data=resp, status=400)
                code = 400
                resp['msg'] = '操作状态不对'
                return Response(data=resp, status=code)
            code = 403
            resp['msg'] = '无操作权限'
            return Response(data=resp, status=code)
        code = 400
        resp['msg'] = '操作对象不存在'
        return Response(data=resp, status=code)
