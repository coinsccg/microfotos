# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 16:57
@Auth: money
@File: route
"""
from flask import Blueprint
from middleware.auth import auth_user_login
from controller.apps.order import app_order_api

url = "/api/v1"
apps_order = Blueprint("apps_order", __name__, url_prefix="")


# 加入购物车接口
@apps_order.route(f"{url}/car/add", methods=["POST"])
@auth_user_login
def user_car_add():
    return app_order_api.post_add_car()


# 删除购物车接口
@apps_order.route(f"{url}/car/delete", methods=["DELETE"])
@auth_user_login
def user_car_delete():
    return app_order_api.delete_user_car_goods()


# 购物车列表接口
@apps_order.route(f"{url}/car/list", methods=["GET"])
@auth_user_login
def user_car_list():
    return app_order_api.get_user_car_list()


# 购物车合并订单接口
@apps_order.route(f"{url}/car/merge", methods=["PUT"])
@auth_user_login
def user_car_merge():
    return app_order_api.post_car_generate_order()


# 订单列表接口
@apps_order.route(f"{url}/order/list", methods=["GET"])
@auth_user_login
def user_order_list():
    return app_order_api.get_user_order_list()


# 订单详情接口
@apps_order.route(f"{url}/order/detail", methods=["GET"])
@auth_user_login
def user_order_detail():
    return app_order_api.get_order_detail()


# 取消订单接口
@apps_order.route(f"{url}/order/state", methods=["PUT"])
@auth_user_login
def user_order_state():
    return app_order_api.put_cancel_order()


# 订单支付请求参数接口
@apps_order.route(f"{url}/order/payment", methods=["POST"])
@auth_user_login
def order_payment():
    return app_order_api.post_order_payment_param()


# 支付宝回调验证接口
@apps_order.route(f"{url}/alipay/callback", methods=["GET", "POST"])
@auth_user_login
def alipay_callback_verify():
    return app_order_api.post_alipay_callback_verify()


# 微信支付回调验证接口
@apps_order.route(f"{url}/wechat/callback", methods=["GET", "POST"])
@auth_user_login
def wechat_callback_verify():
    return app_order_api.post_wechat_callback_verify()


# 余额支付接口
@apps_order.route(f"{url}/balance/pay", methods=["POST"])
@auth_user_login
def balance_pay():
    return app_order_api.get_balance_payment()


# 余额充值接口
@apps_order.route(f"{url}/balance/recharge", methods=["POST"])
@auth_user_login
def balance_recharge():
    return app_order_api.post_balance_recharge()


# 订单支付时校验图片是否已经购买接口
@apps_order.route(f"{url}/order/pay/verify", methods=["POST"])
@auth_user_login
def order_pay_vierify_pic():
    return app_order_api.post_verify_pic_isbuy()


# 余额充值支付宝回调接口
@apps_order.route(f"{url}/recharge/alipay/callback", methods=["POST"])
@auth_user_login
def balance_recharge_callback_alipay():
    return app_order_api.post_top_up_alipay_callback_verify()


# 余额充值回调接口
@apps_order.route(f"{url}/recharge/wechat/callback", methods=["POST"])
@auth_user_login
def balance_recharge_callback_wechat():
    return app_order_api.post_top_up_wechat_callback_verify()


# 用户未付款订单数接口
@apps_order.route(f"{url}/notpay/order/count", methods=["GET"])
@auth_user_login
def user_notpay_count_order():
    return app_order_api.get_not_complete_order_count()


# 订单退款申请
@apps_order.route(f"{url}/order/refund/apply", methods=["POST"])
@auth_user_login
def orderRefundApply():
    return app_order_api.postOrderRefund()


# 用户支付密码检查
@apps_order.route(f"{url}/user/info/verify", methods=["GET"])
@auth_user_login
def verifyPasswordAndMobile():
    return app_order_api.verifyPassword()
