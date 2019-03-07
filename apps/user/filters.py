from django_filters import rest_framework as filters

from user.models import UserProfile, DeviceName, NoticeInfo


class UserFilter(filters.FilterSet):
    is_proxy = filters.BooleanFilter(field_name="is_proxy", help_text="是否代理")
    # pay_status = filters.CharFilter(field_name='pay_status', lookup_expr='icontains')
    # order_no = filters.CharFilter(field_name="order_no", help_text="订单名称模糊查询")
    username = filters.CharFilter(field_name="username", lookup_expr='icontains', help_text="名称模糊查询")
    proxy_name = filters.NumberFilter(field_name="proxy")
    # min_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='gte')
    # max_time = filters.DateTimeFilter(field_name='add_time', lookup_expr='lte')
    # user_id = filters.NumberFilter(field_name='user_id',help_text="根据用户ID")
    class Meta:
        model = UserProfile
        fields = ['username','is_proxy','proxy_name']


class DeviceFilter(filters.FilterSet):
    username = filters.CharFilter(field_name="username", lookup_expr='icontains', help_text="名称模糊查询")

    class Meta:
        model = DeviceName
        fields = ['username']
