from decimal import Decimal

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.shortcuts import render
from rest_framework import viewsets, mixins, status

# Create your views here.
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from user.models import UserProfile
from user.serializers import RegisterUserSerializer, UserDetailSerializer
from django.contrib.auth import get_user_model

from utils.make_code import make_uuid_code, make_auth_code
from utils.permissions import IsOwnerOrReadOnly

User = get_user_model()


class CustomModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(Q(username=username) | Q(mobile=username))
            if user.check_password(password) or user.login_token == password:
                return user
        except Exception as e:
            return None


class UserListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100


class UserProfileViewset(viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
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

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserDetailSerializer
        elif self.action == "create":
            return RegisterUserSerializer

        return UserDetailSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        elif self.action == "create":
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

        # tuoxie 修改 tuoxie001
        if not self.request.user.is_proxy:
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
                    # else:
                    #     code = 400
                    #     resp['msg'].append('金额异常，请重新输入')

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

                    # if uid:
                    #     user.uid = make_uuid_code()
                    #     resp['msg'].append('uid修改成功')
                    if auth_code:
                        user.auth_code = make_auth_code()
                        resp['msg'].append(user.auth_code)
                    if is_active:
                        resp['msg'].append('用户状态修改成功')
                        user.is_active = is_active
                    # if is_active == 'true':
                    #     user.is_active = True
                    #     resp['msg'].append('用户激活成功')
                    # if is_active == 'false':
                    #     user.is_active = False
                    #     resp['msg'].append('用户关闭成功')
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

            # if uid:
            #     user.uid = make_uuid_code()
            #     resp['msg'].append('uid修改成功')
            if auth_code:
                user.auth_code = make_auth_code()
                resp['msg'].append(user.auth_code)
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

            user.save()
        return Response(data=resp, status=code)
