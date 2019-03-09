from django_filters import rest_framework as filters
from .models import OrderInfo, WithDrawMoney
from user.models import BankInfo, OperateLog


class OrdersFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name="total_amount", lookup_expr='lte', help_text="最大金额")
    pay_status = filters.CharFilter(field_name='pay_status', lookup_expr='icontains')
    order_no = filters.CharFilter(field_name="order_no", help_text="订单名称模糊查询")
    order_id = filters.CharFilter(field_name="order_id", help_text="商家订单名称模糊查询")
    user_msg = filters.CharFilter(field_name="user_msg", lookup_expr='icontains')
    min_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='gte')
    max_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='lte')
    user_id = filters.NumberFilter(field_name='user_id', help_text="根据用户ID")

    class Meta:
        model = OrderInfo
        fields = ['min_price', 'max_price', 'order_no', 'order_id', 'min_time', 'max_time', 'user_msg', 'user_id']


class WithDrawFilter(filters.FilterSet):
    min_money = filters.NumberFilter(field_name='money', lookup_expr='gte')
    max_money = filters.NumberFilter(field_name="money", lookup_expr='lte', help_text="最大金额")
    withdraw_status = filters.CharFilter(field_name='withdraw_status', lookup_expr='icontains')
    withdraw_no = filters.CharFilter(field_name="withdraw_no", help_text="提现单号名称模糊查询")
    user_msg = filters.CharFilter(field_name="user_msg", lookup_expr='icontains')
    min_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='gte')
    max_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='lte')
    user_id = filters.NumberFilter(field_name='user_id', help_text="根据用户ID")

    class Meta:
        model = WithDrawMoney
        fields = ['min_money', 'max_money', 'user_msg', 'min_time', 'max_time', 'user_msg', 'withdraw_no', 'user_id']


class BankFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='icontains', help_text="名称查询")
    mobile = filters.CharFilter(field_name="mobile", lookup_expr='icontains', help_text="手机号查询")
    account_num = filters.CharFilter(field_name="account_num", lookup_expr='icontains', help_text="账号查询")

    class Meta:
        model = BankInfo
        fields = ['name', 'mobile', 'account_num']


class LogFilter(filters.FilterSet):
    content = filters.CharFilter(field_name="content", lookup_expr='icontains', help_text="名称查询")
    min_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='gte')
    max_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='lte')
    user_id = filters.NumberFilter(field_name='user_id', help_text="根据用户ID")
    type_name = filters.NumberFilter(field_name='operate_type',help_text="根据类型过滤")
    class Meta:
        model = OperateLog
        fields = ['content','min_time','max_time','user_id','type_name']
