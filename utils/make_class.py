from pay.settings import FONT_DOMAIN
from trade.models import OrderInfo


class ChooseChannel(object):
    def __init__(self, channel,id,order_no,total_amount,user_msg,order_id,bank_tel,account_num):
        self.channel = channel
        self.id = id
        self.order_no=order_no
        self.total_amount=total_amount
        self.user_msg = user_msg
        self.total_amount = total_amount
        self.order_id = order_id
        self.order_id = order_id
        self.account_num = account_num
        self.bank_tel = bank_tel

    def make_choose(self):
        if self.channel == 'atb':
            order = OrderInfo()
            order.user_id = self.id
            order.order_no = self.order_no
            order.pay_status = 'PAYING'
            order.total_amount = self.total_amount
            order.user_msg = self.user_msg
            order.order_id = self.order_id
            order.bank_tel = self.bank_tel
            order.account_num = self.account_num
            pay_url = FONT_DOMAIN + '/pay/' + self.order_no
            order.pay_url = pay_url
            order.receive_way = '0'
            order.save()
            return self.channel
        # elif self.channel == 'alipay':
        #     pass
        else:
            return ''
