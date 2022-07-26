# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 14:57
@Auth: money
@File: route
"""
from flask import Blueprint
from middleware.auth import auth_admin_login
from controller.admin.login import admin_login_api

url = "/api/v1"
admin_login = Blueprint("admin_login", __name__, url_prefix="")


# 后台登录接口
@admin_login.route(f"{url}/admin/login", methods=["POST"])
def admin_login_user():
    return admin_login_api.post_admin_login()


# 后台管理员修改密码接口
@admin_login.route(f"{url}/admin/alter/password", methods=["PUT"])
@auth_admin_login
def admin_alter_password():
    return admin_login_api.put_admin_password()
