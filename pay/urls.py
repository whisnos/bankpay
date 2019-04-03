"""pay URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from django.conf.urls import url
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token

from user.views import UserProfileViewset, device_login, NoticeInfoViewset, ChartInfoViewset, version, LogsViewset, \
    CallBackViewset, UserAccountsViewset
from trade.views import OrderViewset, BankViewset, GetPayView, VerifyView, WithDrawViewset, VerifyViewset, \
    pay, DevicesViewset, mobile_pay, QueryOrderView, ReleaseViewset,test,get_info,OrderInfoViewset

route = DefaultRouter()
route.register(r'users', UserProfileViewset, base_name="users") # users
route.register(r'accounts', UserAccountsViewset, base_name="accounts") # accounts
route.register(r'orders', OrderViewset, base_name="orders")
route.register(r'banks', BankViewset, base_name="banks")
route.register(r'drawings', WithDrawViewset, base_name='moneys')
route.register(r'devices', DevicesViewset, base_name='devices')
route.register(r'verifys', VerifyViewset, base_name='verifys')  # 验证 手机揽收 后的信息
route.register(r'orderinfo', OrderInfoViewset, base_name='orderinfo')  # 获取订单信息
route.register(r'notices', NoticeInfoViewset, base_name="notices")
route.register(r'charts', ChartInfoViewset, base_name="charts")
route.register(r'releases', ReleaseViewset, base_name="releases")
route.register(r'logs', LogsViewset, base_name="logs")
route.register(r'backs', CallBackViewset, base_name="backs")

urlpatterns = [
    url(r'^', include(route.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^login/$', obtain_jwt_token),
    url(r'^get_pay/$', GetPayView.as_view(), name="get_pay"),
    url(r'^verify_pay/$', VerifyView.as_view(), name="verify_pay"),
    url(r'^pay/$', pay, name="pay"),
    url(r'^mobile_pay/$', mobile_pay, name="mobile_pay"),
    url(r'^device_login/$', device_login, name='device_login'),
    url(r'^version/$', version, name='version'),
    url(r'^test/$', test, name='test'),
    url(r'^get_info/$', get_info, name='get_info'),
    # 查询订单接口
    url(r'^query_order/$', QueryOrderView.as_view(), name="query_order"),
]
