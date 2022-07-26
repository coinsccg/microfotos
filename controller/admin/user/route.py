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
from controller.admin.user import admin_user_api
from controller.admin import log_records

url = "/api/v1"
admin_user = Blueprint("admin_user", __name__, url_prefix="")


@admin_user.after_request
def log(response):
    method = request.method
    status = response.status[:3]
    if status == "200" and (method in ["POST", "PUT", "DELETE"]):
        permission_id = request.headers.get("permission_id")
        log_records(permission_id)
    return response


# 后台用户列表筛选接口
@admin_user.route(f"{url}/admin/user/filter", methods=["GET"])
@auth_admin_login
def admin_user_filter():
    return admin_user_api.get_user_filter_list()


# 用户分组类型接口
@admin_user.route(f"{url}/admin/user/group", methods=["GET"])
@auth_admin_login
def admin_user_group_list():
    return admin_user_api.get_user_group_list()


# 后台用户冻结恢复接口
@admin_user.route(f"{url}/admin/user/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_user_state():
    return admin_user_api.put_user_state()


# 后台用户移动组接口
@admin_user.route(f"{url}/admin/user/group", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_user_group():
    return admin_user_api.put_user_group()


# 后台用户详情接口
@admin_user.route(f"{url}/admin/user/detail", methods=["GET"])
@auth_admin_login
def admin_user_detail():
    return admin_user_api.get_user_detail()


# 后台用户重置密码接口
@admin_user.route(f"{url}/admin/user/reset/password", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_user_reset_password():
    return admin_user_api.put_user_password()


# 后台用户更改手机接口
@admin_user.route(f"{url}/admin/user/alter/mobile", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_user_alter_mobile():
    return admin_user_api.put_user_mobile()


# 后台给用户发送消息接口
@admin_user.route(f"{url}/admin/user/send/message", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_user_send_message():
    return admin_user_api.post_user_message()


# 后台用户余额操作接口
@admin_user.route(f"{url}/admin/user/balance/operation", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_user_balance_operatin():
    return admin_user_api.put_user_balance_operation()


# 后台用户余额记录接口
@admin_user.route(f"{url}/admin/user/balance/record", methods=["GET"])
@auth_admin_login
@auth_amdin_role
def admin_user_balance_record():
    return admin_user_api.get_user_balance_records()


# 后台机构用户列表接口
@admin_user.route(f"{url}/admin/org/list", methods=["GET"])
@auth_admin_login
def admin_org_list():
    return admin_user_api.get_org_list()


# 后台机构用户列表筛选接口
@admin_user.route(f"{url}/admin/org/filter", methods=["GET"])
@auth_admin_login
def admin_org_filter():
    return admin_user_api.get_org_filter_list()


# 后台机构名接口
@admin_user.route(f"{url}/admin/org/name", methods=["GET"])
@auth_admin_login
def admin_org_name():
    return admin_user_api.get_org_name_list()


# 后台创建机构接口
@admin_user.route(f"{url}/admin/create/org", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_create_org():
    return admin_user_api.post_create_org_account()


# 舍弃 后台用户待审核列表接口
@admin_user.route(f"{url}/admin/user/audit", methods=["GET"])
@auth_admin_login
def admin_user_audit():
    return admin_user_api.get_user_audit()


# 后台用户待审核列表搜索接口
@admin_user.route(f"{url}/admin/user/audit/filter", methods=["GET"])
@auth_admin_login
def admin_user_audit_filter():
    return admin_user_api.get_user_audit_filter()


# 后台用户待审核列表审核接口
@admin_user.route(f"{url}/admin/user/audit/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_user_audit_state():
    return admin_user_api.put_user_audit_state()


# 后台用户待审核详情接口
@admin_user.route(f"{url}/admin/user/audit/detail", methods=["GET"])
@auth_admin_login
def admin_user_audit_detail():
    return admin_user_api.get_user_audit_detail()


@admin_user.route(f"{url}/admin/user/forbidden", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_user_forbidden_insert():
    return admin_user_api.postForbiddenSpeech()


@admin_user.route(f"{url}/admin/user/forbidden", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_user_forbidden_update():
    return admin_user_api.updateForbiddenSpeech()
