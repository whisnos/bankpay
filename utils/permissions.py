from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """

    # obj是数据库取出来的
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        # 如果不是修改数据类型的请求GET', 'HEAD', 'OPTIONS，直接返回
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must have an attribute named `owner`.
        # 判断是否是同一个用户
        return obj.user == request.user or request.user.is_superuser


# login 增加字段
def jwt_response_payload_handler(token, user=None, request=None):
    """为返回的结果添加用户相关信息"""
    if not user.level:
        user.level=None

    return {
        'token': token,
        'username': user.username,
        'level': user.level,
    }
