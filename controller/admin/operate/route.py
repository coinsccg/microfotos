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
from controller.admin.operate import admin_operating_api
from controller.admin import log_records

url = "/api/v1"
admin_operate = Blueprint("admin_operate", __name__, url_prefix="")


@admin_operate.after_request
def log(response):
    method = request.method
    status = response.status[:3]
    if status == "200" and (method in ["POST", "PUT", "DELETE"]):
        permission_id = request.headers.get("permission_id")
        log_records(permission_id)
    return response


# 后台平台定价信息展示接口
@admin_operate.route(f"{url}/admin/price/show", methods=["GET"])
@auth_admin_login
def admin_platform_price_show():
    return admin_operating_api.get_platform_info()


# 后台平台定价接口
@admin_operate.route(f"{url}/admin/price", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_platform_price():
    return admin_operating_api.post_platform_pricing()


# 后台推荐作品列表接口
@admin_operate.route(f"{url}/admin/recomm/list", methods=["GET"])
@auth_admin_login
def admin_recomm_list():
    return admin_operating_api.get_recomm_works_list()


# 后台推荐作品删除接口
@admin_operate.route(f"{url}/admin/recomm/delete", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_recomm_delete():
    return admin_operating_api.put_recomm_state()


# 后台推荐作品选择接口
@admin_operate.route(f"{url}/admin/recomm/option", methods=["GET"])
@auth_admin_login
def admin_recomm_option():
    return admin_operating_api.get_option_works_list()


# 后台推荐作品选择搜索接口
@admin_operate.route(f"{url}/admin/recomm/option/search", methods=["GET"])
@auth_admin_login
def admin_recomm_option_search():
    return admin_operating_api.get_option_works_list_search()


# 后台添加推荐作品接口
@admin_operate.route(f"{url}/admin/recomm/add", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_recomm_add():
    return admin_operating_api.post_add_recomm_works()
