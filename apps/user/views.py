import json, time
from decimal import Decimal

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status

# Create your views here.
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from trade.models import OrderInfo
from trade.serializers import OrderListSerializer
from user.filters import UserFilter
from user.models import UserProfile, DeviceName, NoticeInfo, VersionInfo
from user.serializers import RegisterUserSerializer, UserDetailSerializer, UpdateUserSerializer, NoticeInfoSerializer
from django.contrib.auth import get_user_model

from utils.make_code import make_uuid_code, make_auth_code
from utils.permissions import IsOwnerOrReadOnly

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
                print(555555)
                if user.check_password(password):
                    return user
                else:
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


class UserProfileViewset(mixins.ListModelMixin, viewsets.GenericViewSet, mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin):
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
    queryset = UserProfile.objects.all()
    serializer_class = RegisterUserSerializer
    pagination_class = UserListPagination
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    # JWT认证
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    filter_backends = (DjangoFilterBackend,)
    filter_class = UserFilter

    def get_queryset(self):
        user = self.request.user
        return UserProfile.objects.filter(proxy_id=user.id).order_by('id')

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserDetailSerializer
        elif self.action == "create":
            return RegisterUserSerializer
        elif self.action == "list":
            return UserDetailSerializer
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
        # uid = self.request.data.get('uid', '')
        auth_code = self.request.data.get('auth_code', '')
        is_active = self.request.data.get('is_active', '')
        print('auth_code', auth_code)
        service_rate = self.request.data.get('service_rate', '')

        if self.request.user.is_superuser:
            if get_proxyid:
                user_queryset = UserProfile.objects.filter(id=get_proxyid)
                if user_queryset:
                    if password == password2:
                        if password:
                            user = user_queryset[0]
                            user.set_password(password)
                            resp['msg'].append('密码修改成功')
                            user.save()
                    else:
                        code = 404
                        resp['msg'].append('输入密码不一致')

        # tuoxie 修改 tuoxie001
        if not self.request.user.is_proxy and not self.request.user.is_superuser:
            id_list = [user_obj.id for user_obj in UserProfile.objects.filter(proxy_id=self.request.user.id)]
            if get_proxyid:
                if int(get_proxyid) in id_list:
                    user = UserProfile.objects.filter(id=get_proxyid)[0]
                    if add_money:
                        user.total_money = '%.2f' % (Decimal(user.total_money) + Decimal(add_money))
                        resp['msg'].append('加款成功')
                    if minus_money:
                        if Decimal(minus_money) < Decimal(user.total_money):
                            user.total_money = '%.2f' % (Decimal(user.total_money) - Decimal(minus_money))
                            resp['msg'].append('扣款成功')
                        else:
                            code = 404
                            resp['msg'].append('余额不足，扣款失败')

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
                        user.service_rate = float(service_rate)
                    user.save()
                else:
                    code = 404
                    resp['msg'].append('修改代理号不存在')

        # 修改tuoxie本身数据
        if not get_proxyid and not self.request.user.is_proxy:
            qq = self.request.data.get('qq', '')
            user = self.get_object()

            if add_money:
                user.total_money = '%.2f' % (Decimal(user.total_money) + Decimal(add_money))
                resp['msg'].append('加款成功')
            if minus_money:
                if Decimal(minus_money) < Decimal(user.total_money):
                    user.total_money = '%.2f' % (Decimal(user.total_money) - Decimal(minus_money))
                    resp['msg'].append('扣款成功')
                else:
                    code = 404
                    resp['msg'].append('余额不足，扣款失败')

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
                        mixins.CreateModelMixin):
    serializer_class = NoticeInfoSerializer
    queryset = NoticeInfo.objects.all().order_by('-add_time')
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    pagination_class = UserListPagination

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
        if not obj.is_proxy:
            user_qset = UserProfile.objects.filter(proxy_id=obj.id)
            for user in user_qset:
                userid_list.append(user.id)
        elif obj.is_proxy:
            userid_list.append(obj.id)
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
