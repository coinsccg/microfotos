# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 14:57
@Auth: money
@File: route
"""
from flask import Blueprint
from middleware.auth import auth_admin_login
from controller.admin.index import admin_index_api

url = "/api/v1"
admin_index = Blueprint("admin_index", __name__, url_prefix="")


# 后台首页顶部统计接口
@admin_index.route(f"{url}/admin/index/collect", methods=["GET"])
@auth_admin_login
def admin_index_top_collect():
    return admin_index_api.get_top_statistics()


# 后台首页趋势统计接口
@admin_index.route(f"{url}/admin/index/trend", methods=["GET"])
@auth_admin_login
def admin_index_trend_collect():
    return admin_index_api.get_data_statistics()
