from rest_framework import permissions

from user.models import OperateLog


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
    print('token', token)
    if not user.level:
        user.level = None
    if request.META.get('HTTP_X_FORWARDED_FOR',''):
        print(1)
        ip = request.META.get('HTTP_X_FORWARDED_FOR','')
    else:
        print(2)
        ip = request.META.get('REMOTE_ADDR','')
    # 引入日志
    log = MakeLogs()
    content = '用户：' + str(user.username) + ' 登录ip为：' + str(ip)
    log.add_logs('0', content, user.id)
    return {
        'token': token,
        'username': user.username,
        'level': user.level,
    }


class MakeLogs(object):
    def add_logs(self,operate_type,content,user_id):
        log_obj = OperateLog()
        log_obj.operate_type = operate_type
        log_obj.content = content
        log_obj.user_id = user_id
        log_obj.save()
        return True
