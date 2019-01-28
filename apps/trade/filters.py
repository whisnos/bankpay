from django_filters import rest_framework as filters
from .models import OrderInfo, WithDrawMoney


class OrdersFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name="total_amount", lookup_expr='lte', help_text="最大金额")
    pay_status = filters.CharFilter(field_name='pay_status', lookup_expr='icontains')
    order_no = filters.CharFilter(field_name="order_no", help_text="订单名称模糊查询")
    order_id = filters.CharFilter(field_name="order_id", help_text="商家订单名称模糊查询")
    user_msg = filters.CharFilter(field_name="user_msg", lookup_expr='icontains')
    min_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='gte')
    max_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='lte')

    class Meta:
        model = OrderInfo
        fields = ['min_price', 'max_price', 'order_no', 'order_id','min_time', 'max_time', 'user_msg']


class WithDrawFilter(filters.FilterSet):
    min_money = filters.NumberFilter(field_name='money', lookup_expr='gte')
    max_money = filters.NumberFilter(field_name="money", lookup_expr='lte', help_text="最大金额")
    withdraw_status = filters.CharFilter(field_name='withdraw_status', lookup_expr='icontains')
    withdraw_no = filters.CharFilter(field_name="withdraw_no", help_text="提现单号名称模糊查询")
    user_msg = filters.CharFilter(field_name="user_msg", lookup_expr='icontains')
    min_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='gte')
    max_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='lte')

    class Meta:
        model = WithDrawMoney
        fields = ['min_money', 'max_money', 'user_msg', 'min_time', 'max_time', 'user_msg','withdraw_no']