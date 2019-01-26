from decimal import Decimal

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
        today_receive: 今日收款 包括成功与否 ---
        today_count_num: 今日总订单数 所有 包括成功与否 ---
        today_count_success_num: 今日订单数(仅含成功订单)
    '''
    queryset = UserProfile.objects.all()
    serializer_class = RegisterUserSerializer
    pagination_class = UserListPagination
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
            return []
        else:
            return []

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        resp={'msg':[]}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = self.request.data.get('password', '')
        password2 = self.request.data.get('password2', '')
        notify_url = self.request.data.get('notify_url', '')
        add_money = self.request.data.get('add_money', '')
        minus_money = self.request.data.get('minus_money', '')
        qq = self.request.data.get('qq', '')
        user = self.get_object()
        if password == password2:
            if password:
                user.set_password(password)
                resp['msg'].append('密码修改成功')
        else:
            resp['msg'].append('输入密码不一致')
        if notify_url:
            user.notify_url = notify_url
            resp['msg'].append('回调修改成功')
        if qq:
            user.qq = qq
        if add_money:
            user.total_money = '%.2f' % (Decimal(user.total_money) + Decimal(add_money))
            resp['msg'].append('加款成功')
        if minus_money:
            user.total_money = '%.2f' % (Decimal(user.total_money) - Decimal(minus_money))
            resp['msg'].append('扣款成功')
        user.save()
        return Response(data=resp,status=status.HTTP_200_OK)
