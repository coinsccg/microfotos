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
from controller.admin.system import admin_system_api
from controller.admin import log_records

url = "/api/v1"
admin_system = Blueprint("admin_system", __name__, url_prefix="")


@admin_system.after_request
def log(response):
    method = request.method
    status = response.status[:3]
    if status == "200" and (method in ["POST", "PUT", "DELETE"]):
        permission_id = request.headers.get("permission_id")
        log_records(permission_id)
    return response


# 后台管理员列表搜索接口
@admin_system.route(f"{url}/admin/manage/search", methods=["GET"])
@auth_admin_login
def admin_manage_search():
    return admin_system_api.get_admin_account_search()


# 后台管理员创建账号接口
@admin_system.route(f"{url}/admin/manage/create", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_manage_create_account():
    return admin_system_api.post_create_account()


# 后台管理员列表删除接口
@admin_system.route(f"{url}/admin/manage/delete", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_manage_list_delete():
    return admin_system_api.put_admin_account_state()


# 后台管理员权限列表接口
@admin_system.route(f"{url}/admin/permission/list", methods=["GET"])
@auth_admin_login
@auth_amdin_role
def admin_manage_permission_list():
    return admin_system_api.get_admin_permission_list()


# 后台管理员重置密码接口
@admin_system.route(f"{url}/admin/reset/password", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_manage_reset_password():
    return admin_system_api.put_admin_password_reset()


# 后台管理员修改信息接口
@admin_system.route(f"{url}/admin/info/alter", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_manage_account_alter():
    return admin_system_api.put_admin_account_alter()


# 后台管理员创建角色接口
@admin_system.route(f"{url}/admin/create/role", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def admin_permission_create_role():
    return admin_system_api.post_add_permissions_role()


# 后台角色编辑接口
@admin_system.route(f"{url}/admin/editor/role", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_permission_create_role_editor():
    return admin_system_api.put_add_permissions_role_editor()


# 后台角色列表接口
@admin_system.route(f"{url}/admin/role/list", methods=["GET"])
@auth_admin_login
def admin_role_list():
    return admin_system_api.get_role_list()


# 后台角色删除接口
@admin_system.route(f"{url}/admin/role/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_role_state():
    return admin_system_api.put_role_state()


# 后台日志列表接口
@admin_system.route(f"{url}/admin/log/list", methods=["GET"])
@auth_admin_login
def admin_log_list():
    return admin_system_api.get_admin_operation_log()


# 系统备份列表接口
@admin_system.route(f"{url}/admin/backup/list", methods=["GET"])
@auth_admin_login
def admin_system_backup_list():
    return admin_system_api.post_system_backup_list()


# 系统备份删除接口
@admin_system.route(f"{url}/admin/backup/state", methods=["DELETE"])
@auth_admin_login
def admin_system_backup_state():
    return admin_system_api.delete_backup_state()


# 系统备份接口
@admin_system.route(f"{url}/admin/system/backup", methods=["POST"])
@auth_admin_login
def admin_system_backup():
    return admin_system_api.post_system_backup()


# 系统还原接口
@admin_system.route(f"{url}/admin/system/reduction", methods=["POST"])
@auth_admin_login
def admin_system_reduction():
    return admin_system_api.post_system_backup_reduction()


@admin_system.route(f"{url}/admin/version", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def adminSystemVersionAdd():
    return admin_system_api.post_version_add()


@admin_system.route(f"{url}/admin/version", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def adminSystemVersionPut():
    return admin_system_api.put_version_info()


@admin_system.route(f"{url}/admin/version", methods=["DELETE"])
@auth_admin_login
@auth_amdin_role
def adminSystemVersionDelete():
    return admin_system_api.put_version_state()


@admin_system.route(f"{url}/admin/version/list", methods=["GET"])
@auth_admin_login
def adminSystemVersionList():
    return admin_system_api.get_version_list()


@admin_system.route(f"{url}/admin/version/no", methods=["GET"])
@auth_admin_login
def adminSystemVersionNoList():
    return admin_system_api.get_version_latest_list()


@admin_system.route(f"{url}/admin/version/no", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def adminSystemVersionNoAdd():
    return admin_system_api.post_latest_version()


@admin_system.route(f"{url}/admin/upload/apk", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def adminSystemUploadApk():
    return admin_system_api.post_upload_apk()
