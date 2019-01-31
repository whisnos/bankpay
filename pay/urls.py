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

from user.views import UserProfileViewset
from trade.views import OrderViewset, BankViewset, GetPayView, VerifyView, AddMoney, WithDrawViewset,VerifyViewset,pay

route = DefaultRouter()
route.register(r'users', UserProfileViewset, base_name="users")
route.register(r'orders', OrderViewset, base_name="orders")
route.register(r'banks', BankViewset, base_name="banks")
route.register(r'drawings',WithDrawViewset,base_name='moneys')
route.register(r'verifys',VerifyViewset,base_name='verifys') # 验证 手机揽收 后的信息

urlpatterns = [
    # path('admin/', admin.site.urls),
    url(r'^', include(route.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^login/', obtain_jwt_token),
    url(r'^get_pay/', GetPayView.as_view(), name="get_pay"),
    url(r'^verify_pay/', VerifyView.as_view(), name="verify_pay"),
    url(r'^add_money/', AddMoney.as_view(), name="add_money"),
    url(r'^pay/', pay, name="pay"),
]