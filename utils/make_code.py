import hashlib
import uuid
import random


def make_uuid_code():
    for i in range(1):
        code = str(uuid.uuid1())
        code = code.replace('-', '')
        return code


def make_draw_code():
    for i in range(1):
        code = str(uuid.uuid1())
        code = code.replace('-', '')
        return code


def make_auth_code(length=32):
    from_str = '12356789ZXCVBNMASDFGHJKLQWERTYUIOPzxcvbnmasdfghjklqwertyuiop'
    new_str = ''
    for i in range(length):
        a = str(random.choice(from_str))
        new_str += a
    return new_str


def make_login_token(length=8):
    from_str = '123567890zxcvbnmasdfghjklqwertyuiop'
    new_str = ''
    for i in range(length):
        a = str(random.choice(from_str))
        new_str += a
    return new_str


def make_short_code(length):
    code_source = '123456789'
    code = ''
    for i in range(length):
        code += code_source[random.randint(0, len(code_source) - 1)]
    return code


# 生成订单号信息
import time


def generate_order_no(userid):
    # "当前时间+userid+随机数"
    short_code = make_short_code(8)
    order_sn = "{time_str}{userid}{randstr}".format(time_str=time.strftime("%Y%m%d%H%M%S"),
                                                    userid=userid, randstr=short_code)
    return order_sn

def make_md5(new_temp):
    m = hashlib.md5()
    m.update(new_temp.encode('utf-8'))
    my_key = m.hexdigest()
    return my_key