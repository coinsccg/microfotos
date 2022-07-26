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
from controller.admin.opinion import admin_opinion_api
from controller.admin import log_records

url = "/api/v1"
admin_opinion = Blueprint("admin_opinion", __name__, url_prefix="")


@admin_opinion.after_request
def log(response):
    method = request.method
    status = response.status[:3]
    if status == "200" and (method in ["POST", "PUT", "DELETE"]):
        permission_id = request.headers.get("permission_id")
        log_records(permission_id)
    return response


# 后台评论列表搜索接口
@admin_opinion.route(f"{url}/admin/comment/search", methods=["GET"])
@auth_admin_login
def admin_comment_list_search():
    return admin_opinion_api.get_report_comment_search()


# 后台评论审核接口
@admin_opinion.route(f"{url}/admin/comment/audit", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_comment_audit():
    return admin_opinion_api.put_report_comment_state()


# 后台评论统计接口
@admin_opinion.route(f"{url}/admin/comment/statistical", methods=["GET"])
@auth_admin_login
def admin_comment_list_statistical():
    return admin_opinion_api.get_report_comment_top()


# 后台敏感词展示接口
@admin_opinion.route(f"{url}/admin/bad/list", methods=["GET"])
@auth_admin_login
def admin_comment_bad_show():
    return admin_opinion_api.get_bad_keyword_list()


# 后台添加敏感关键词接口
@admin_opinion.route(f"{url}/admin/comment/keyword/add", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_comment_keyword_add():
    return admin_opinion_api.post_add_bad_keyword()


# 后台被举报作品数据接口
@admin_opinion.route(f"{url}/admin/report/works", methods=["GET"])
@auth_admin_login
def admin_report_works():
    return admin_opinion_api.get_works_report_number()


# 后台被举报作品列表接口
@admin_opinion.route(f"{url}/admin/report/works/list", methods=["GET"])
@auth_admin_login
def admin_report_works_list():
    return admin_opinion_api.get_report_works_list()


# 后台被举报作品状态修改接口
@admin_opinion.route(f"{url}/admin/report/works/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_report_works_put():
    return admin_opinion_api.put_report_works_state()
