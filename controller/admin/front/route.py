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
from controller.admin.front import admin_front_api
from controller.admin import log_records

url = "/api/v1"
admin_front = Blueprint("admin_front", __name__, url_prefix="")


@admin_front.after_request
def log(response):
    method = request.method
    status = response.status[:3]
    if status == "200" and (method in ["POST", "PUT", "DELETE"]):
        permission_id = request.headers.get("permission_id")
        log_records(permission_id)
    return response


# 后台前台搜索模块按钮展示状态接口
@admin_front.route(f"{url}/admin/search_module", methods=["GET"])
@auth_admin_login
def admin_front_search_module_show():
    return admin_front_api.get_search_module_show()


# 后台前台搜索模块按钮装填修改接口
@admin_front.route(f"{url}/admin/search_module/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_search_module_state():
    return admin_front_api.put_search_model_show()


# 后台前台banner接口
@admin_front.route(f"{url}/admin/banner/list", methods=["GET"])
@auth_admin_login
def admin_front_banner():
    return admin_front_api.get_banner()


# 后台前台banner修改链接接口
@admin_front.route(f"{url}/admin/banner/link", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_banner_link():
    return admin_front_api.putBannerLink()


# 后台前台banner修改序列号接口
@admin_front.route(f"{url}/admin/banner/order", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_banner_order():
    return admin_front_api.put_banner_order()


# 后台前台banner删除接口
@admin_front.route(f"{url}/admin/banner/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_banner_state():
    return admin_front_api.put_banner_state()


# 后台前台banner上传接口
@admin_front.route(f"{url}/admin/banner/upload", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_banner_upload():
    return admin_front_api.post_upload_banner()


# 后台前台置顶作品接口
@admin_front.route(f"{url}/admin/works/top/list", methods=["GET"])
@auth_admin_login
def admin_front_top_works_list():
    return admin_front_api.get_top_works_list()


# 后台前台置顶添加供选列表接口
@admin_front.route(f"{url}/admin/works/top/options", methods=["GET"])
@auth_admin_login
def admin_front_top_works_options():
    return admin_front_api.get_top_options_list()


# 后台前台添加置顶作品接口
@admin_front.route(f"{url}/admin/works/top/add", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_top_works_add():
    return admin_front_api.post_top_works_add()


# 后台前台删除置顶作品接口
@admin_front.route(f"{url}/admin/works/top/delete", methods=["DELETE"])
@auth_admin_login
@auth_amdin_role
def admin_front_top_works_delete():
    return admin_front_api.delete_recommend_top_works()


# 后台前台作品列表接口
@admin_front.route(f"{url}/admin/option/works/list", methods=["GET"])
@auth_admin_login
def admin_front_works_list():
    return admin_front_api.get_option_works_list()


# 后台前台作者列表接口
@admin_front.route(f"{url}/admin/option/author/list", methods=["GET"])
@auth_admin_login
def admin_front_author_list():
    return admin_front_api.get_author_list()


# 后台前台添加推荐作品接口
@admin_front.route(f"{url}/admin/recommend/works/add", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_recommend_works_add():
    return admin_front_api.post_works_recommend_add()


# 后台前台添加推荐作者接口
@admin_front.route(f"{url}/admin/recommend/author/add", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_recommend_author_add():
    return admin_front_api.post_author_recommend_add()


# 后台前台推荐作品列表接口
@admin_front.route(f"{url}/admin/recommend/works/list", methods=["GET"])
@auth_admin_login
def admin_front_recommend_works_list():
    return admin_front_api.get_recommend_works_list()


# 后台前台推荐作者列表接口
@admin_front.route(f"{url}/admin/recommend/author/list", methods=["GET"])
@auth_admin_login
def admin_front_recommend_author_list():
    return admin_front_api.get_recommend_author_list()


# 后台前台删除推荐作品接口
@admin_front.route(f"{url}/admin/recommend/works/delete", methods=["DELETE"])
@auth_admin_login
@auth_amdin_role
def admin_front_recommend_works_delete():
    return admin_front_api.delete_recommend_works()


# 后台前台删除推荐作者接口
@admin_front.route(f"{url}/admin/recommend/author/delete", methods=["DELETE"])
@auth_admin_login
@auth_amdin_role
def admin_front_recommend_author_delete():
    return admin_front_api.delete_recommend_author()


# 后台前台系统推荐规则接口
@admin_front.route(f"{url}/admin/system/recommend/rule", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_system_recommend_rule():
    return admin_front_api.post_system_recommend_rule()


# 后台前台推荐池规则接口
@admin_front.route(f"{url}/admin/contains/recommend/rule", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_contains_recommend_rule():
    return admin_front_api.post_recommend_contains_rule()


# 后台前台系统推荐信息接口
@admin_front.route(f"{url}/admin/system/recommend/info", methods=["GET"])
@auth_admin_login
def admin_front_system_recommend_info():
    return admin_front_api.get_system_recommend_info()


# 后台前台推荐池信息接口
@admin_front.route(f"{url}/admin/contains/recommend/info", methods=["GET"])
@auth_admin_login
def admin_front_contains_recommend_info():
    return admin_front_api.get_recommend_contains_info()


# 后台前台系统推荐规则接口
@admin_front.route(f"{url}/admin/system/recommend", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_system_recommend():
    return admin_front_api.post_system_recommend_rule()


# 后台前台摄影推荐池作品列表接口
@admin_front.route(f"{url}/admin/photo/recommend/works/list", methods=["GET"])
@auth_admin_login
def admin_front_photo_recommend_works_list():
    return admin_front_api.get_photo_recommend_works_list()


# 后台前台摄影推荐池作品添加接口
@admin_front.route(f"{url}/admin/photo/recommend/works/add", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_photo_recommend_works_add():
    return admin_front_api.post_photo_recommend_works_add()


# 后台前台推荐池作品删除接口
@admin_front.route(f"{url}/admin/photo/recommend/works/delete", methods=["DELETE"])
@auth_admin_login
@auth_amdin_role
def admin_front_photo_recommend_works_delete():
    return admin_front_api.delete_photo_recommend_works()


# 后台前台自动添加摄影池状态接口
@admin_front.route(f"{url}/admin/photo/recommend/works/state", methods=["GET"])
@auth_admin_login
def admin_front_photo_recommend_works_state():
    return admin_front_api.get_photo_recommend_state()


# 后台前台自动添加摄影池状态修改接口
@admin_front.route(f"{url}/admin/photo/recommend/works/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_photo_recommend_works_state_alter():
    return admin_front_api.put_photo_recommend_state()


# 后台前台热搜词列表接口
@admin_front.route(f"{url}/admin/hot/keyword", methods=["GET"])
@auth_admin_login
def admin_front_hot_keyword():
    return admin_front_api.get_hot_keyword_list()


# 后台前台添加热词接口
@admin_front.route(f"{url}/admin/keyword/add", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_hot_keyword_add():
    return admin_front_api.post_add_keyword()


# 后台前台删除热搜词接口
@admin_front.route(f"{url}/admin/keyword/delete", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_hot_keyword_delete():
    return admin_front_api.put_delete_keyword()


# 后台前台可选标签列表接口
@admin_front.route(f"{url}/admin/label/list", methods=["GET"])
@auth_admin_login
def admin_front_label_list():
    return admin_front_api.get_label_list()


# 后台前台可选标签优先级接口
@admin_front.route(f"{url}/admin/label/priority", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_label_priority():
    return admin_front_api.put_lable_priority()


# 后台前台可选标签列表接口
@admin_front.route(f"{url}/admin/label/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_label_state():
    return admin_front_api.put_show_label()


# 后台前台置顶文档管理列表接口
@admin_front.route(f"{url}/admin/document/list", methods=["GET"])
@auth_admin_login
def admin_front_document_list():
    return admin_front_api.get_agreement_list()


# 后台前台置顶文档编辑接口
@admin_front.route(f"{url}/admin/document/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_front_document_editor():
    return admin_front_api.put_agreement_editor()


# 后台前台置顶文档上传接口
@admin_front.route(f"{url}/admin/document/upload", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_front_document_upload():
    return admin_front_api.upload_docx_file()


@admin_front.route(f"{url}/admin/kw", methods=["GET"])
@auth_admin_login
def getAdminFrontKeywordState():
    return admin_front_api.getHotKeywordState()


@admin_front.route(f"{url}/admin/kw", methods=["PUT"])
@auth_admin_login
def putAdminFrontKeywordState():
    return admin_front_api.putHotKeywordState()


@admin_front.route(f"{url}/photo/rule", methods=["GET"])
@auth_admin_login
def getAdminFrontPhotoRule():
    return admin_front_api.getPhotoRule()


@admin_front.route(f"{url}/photo/rule", methods=["PUT"])
@auth_admin_login
def putAdminFrontPhotoRule():
    return admin_front_api.putPhotoRule()