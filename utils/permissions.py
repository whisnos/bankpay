from rest_framework import permissions

from user.models import OperateLog


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_superuser


# login 增加字段
def jwt_response_payload_handler(token, user=None, request=None):
    """为返回的结果添加用户相关信息"""
    if not user.level:
        user.level = None
    if request.META.get('HTTP_X_FORWARDED_FOR',''):
        print('HTTP_X_FORWARDED_FOR')
        ip = request.META.get('HTTP_X_FORWARDED_FOR','')
    else:
        print('REMOTE_ADDR')
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
