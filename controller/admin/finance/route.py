# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 14:57
@Auth: money
@File: route
"""
from flask import Blueprint
from flask import request
from middleware.auth import auth_amdin_role
from middleware.auth import auth_admin_login
from controller.admin.finance import admin_finance_api
from controller.admin import log_records

url = "/api/v1"
admin_finance = Blueprint("admin_finance", __name__, url_prefix="")


@admin_finance.after_request
def log(response):
    method = request.method
    status = response.status[:3]
    if status == "200" and (method in ["POST", "PUT", "DELETE"]):
        permission_id = request.headers.get("permission_id")
        log_records(permission_id)
    return response


# 后台订单列表接口
@admin_finance.route(f"{url}/admin/finance/list", methods=["GET"])
@auth_admin_login
def admin_finance_order_list():
    return admin_finance_api.get_order_list()


# 后台订单退款接口
@admin_finance.route(f"{url}/admin/finance/refund", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_finance_order_refund():
    return admin_finance_api.put_order_refund_first()


# 后台订单详情接口
@admin_finance.route(f"{url}/admin/finance/detail", methods=["GET"])
@auth_admin_login
def admin_finance_order_detail():
    return admin_finance_api.get_order_detail()


# 后台提现记录接口
@admin_finance.route(f"{url}/admin/finance/withdrawal", methods=["GET"])
@auth_admin_login
def admin_finance_withdrawal_records():
    return admin_finance_api.get_withdrawal_records()


# 后台充值记录接口
@admin_finance.route(f"{url}/admin/finance/recharge", methods=["GET"])
@auth_admin_login
def admin_finance_recharge_records():
    return admin_finance_api.get_order_recharge()


# 后台充值渠道接口
@admin_finance.route(f"{url}/admin/finance/recharge/channel", methods=["GET"])
@auth_admin_login
def admin_finance_recharge_channel():
    return admin_finance_api.get_recharge_channel()


# 后台提现审核列表接口
@admin_finance.route(f"{url}/admin/finance/withdrawal/audit", methods=["GET"])
@auth_admin_login
def admin_finance_withdrawal_audit():
    return admin_finance_api.get_withdrawal_records_audit()


# 后台提现审核接口
@admin_finance.route(f"{url}/admin/finance/withdrawal/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_finance_withdrawal_state():
    return admin_finance_api.put_withdrawal_records_state()


# 后台提现记录导出接口
@admin_finance.route(f"{url}/admin/finance/withdrawal/export", methods=["GET"])
@auth_admin_login
@auth_amdin_role
def admin_finance_withdrawal_export():
    return admin_finance_api.get_withdrawal_records_export()


# 后台充值记录导出接口
@admin_finance.route(f"{url}/admin/finance/recharge/export", methods=["GET"])
@auth_admin_login
@auth_amdin_role
def admin_finance_recharge_export():
    return admin_finance_api.get_order_recharge_export()


# 后台提现记录导出接口
@admin_finance.route(f"{url}/admin/finance/audit/export", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_finance_withdrawal_audit_export():
    return admin_finance_api.post_withdrawal_records_audit_export()


# 后台可提现银行接口
@admin_finance.route(f"{url}/admin/finance/recharge/bank", methods=["POST"])
@auth_admin_login
def admin_finance_withdrawal_bank():
    return admin_finance_api.post_withdrawal_bank()


# 后台可提现银行列表接口
@admin_finance.route(f"{url}/admin/finance/recharge/bank/list", methods=["GET"])
@auth_admin_login
def admin_finance_withdrawal_bank_list():
    return admin_finance_api.get_bank_list()


# 支付宝退款回调
@admin_finance.route(f"{url}/refund/alipay/callback", methods=["POST", "GET"])
@auth_admin_login
def alipayRefundCallback():
    return admin_finance_api.alipayRefundCallback()


# 微信退款回调
@admin_finance.route(f"{url}/refund/wechat/callback", methods=["POST", "GET"])
@auth_admin_login
def wechatRefundCallback():
    return admin_finance_api.wechatRefundCallback()
