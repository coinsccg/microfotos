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
from controller.admin.works import admin_works_api
from controller.admin import log_records
from initialize import log

url = "/api/v1"
admin_works = Blueprint("admin_works", __name__, url_prefix="")


@admin_works.after_request
def log(response):
    try:
        method = request.method
        status = response.status[:3]
        if status == "200" and (method in ["POST", "PUT", "DELETE"]):
            permission_id = request.headers.get("permission_id")
            log_records(permission_id)
        return response
    except Exception as e:
        log.error(e)


# 后台内容管理图片素材列表接口
@admin_works.route(f"{url}/admin/material/pic/list", methods=["GET"])
@auth_admin_login
def admin_material_list():
    return admin_works_api.get_admin_pic_material_list()


# 后台内容管理图片素材删除接口
@admin_works.route(f"{url}/admin/material/pic/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_material_state():
    return admin_works_api.put_pic_material_state()


# 后台内容管理图片素材详情接口
@admin_works.route(f"{url}/admin/material/pic/detail", methods=["GET"])
@auth_admin_login
def admin_material_detail():
    return admin_works_api.get_pic_material_detail()


# 后台内容管理图片素材编辑接口
@admin_works.route(f"{url}/admin/material/pic/editor", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_material_editor():
    return admin_works_api.put_pic_material()


# 舍弃 后台内容管理音频素材列表接口
@admin_works.route(f"{url}/admin/material/audio/list", methods=["GET"])
@auth_admin_login
def admin_audio_list():
    return admin_works_api.get_audio_material_list()


# 舍弃 后台内容管理音频素材删除接口
@admin_works.route(f"{url}/admin/material/audio/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_audio_state():
    return admin_works_api.put_audio_material_state()


# 舍弃 后台内容管理音频素材详情接口
@admin_works.route(f"{url}/admin/material/audio/detail", methods=["GET"])
@auth_admin_login
def admin_audio_detail():
    return admin_works_api.get_audio_material_detail()


# 舍弃 后台内容管理音频素材编辑接口
@admin_works.route(f"{url}/admin/material/audio/editor", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_audio_editor():
    return admin_works_api.put_audio_material()


# 舍弃 后台内容管理音频素材封面更新接口
@admin_works.route(f"{url}/admin/material/audio/cover", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_audio_cover():
    return admin_works_api.put_audio_material_cover()


# 后台内容管理图片、图集、图文作品列表接口
@admin_works.route(f"{url}/admin/works/list", methods=["GET"])
@auth_admin_login
def admin_pic_atlas_list():
    return admin_works_api.get_all_works_list()


# 后台内容管理图片、图集作品状态接口
@admin_works.route(f"{url}/admin/works/state", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_pic_atlas_state():
    return admin_works_api.put_pic_works_state()


# 后台内容管理图片作品编辑接口
@admin_works.route(f"{url}/admin/works/pic/editor", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_pic_editor():
    return admin_works_api.put_pic_works_info()


# 后台内容管理作品审核列表接口
@admin_works.route(f"{url}/admin/works/audit/list", methods=["GET"])
@auth_admin_login
def admin_works_audit_list():
    return admin_works_api.get_works_audit_list()


# 后台内容管理作品审核接口
@admin_works.route(f"{url}/admin/works/audit", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_works_audit():
    return admin_works_api.put_pic_works_autio_state()


# 后台内容管理图片作品详情接口
@admin_works.route(f"{url}/admin/works/pic/detail", methods=["GET"])
@auth_admin_login
def admin_works_pic_detail():
    return admin_works_api.get_pic_works_detail()


# 后台内容管理图集作品详情接口
@admin_works.route(f"{url}/admin/works/atlas/detail", methods=["GET"])
@auth_admin_login
def admin_works_atlas_detail():
    return admin_works_api.get_atals_detail()


# 后台内容管理图集作品详情图片素材库接口
@admin_works.route(f"{url}/admin/atlas/material/list", methods=["GET"])
@auth_admin_login
def admin_atlas_detail_material():
    return admin_works_api.get_altas_deital_material_list()


# 后台内容管理图集作品详情添加图片接口
@admin_works.route(f"{url}/admin/atlas/pic/add", methods=["PUT"])
@auth_admin_login
def admin_atlas_detail_add_pic_id():
    return admin_works_api.put_altas_works_pic_id()


# 后台内容管理图集作品详情删除图片接口
@admin_works.route(f"{url}/admin/atlas/pic/delete", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_atlas_detail_pic_delete():
    return admin_works_api.put_altas_works_pic_delete()


# 后台内容管理图集作品详情编辑接口
@admin_works.route(f"{url}/admin/works/atlas/editor", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def admin_atlas_detail_editor():
    return admin_works_api.put_altas_works_editor()


# 后台内容管理图文作品详情接口
@admin_works.route(f"{url}/admin/works/article/detail", methods=["GET"])
@auth_admin_login
def admin_works_article_detail():
    return admin_works_api.get_article_works_detail()


# 后台音乐上传
@admin_works.route(f"{url}/admin/music/upload", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def adminMusicUpload():
    return admin_works_api.postUploadMusic()


@admin_works.route(f"{url}/admin/music", methods=["POST"])
@auth_admin_login
@auth_amdin_role
def postAdminMusicInfo():
    return admin_works_api.postUploadMusicInfo()


@admin_works.route(f"{url}/admin/music", methods=["PUT"])
@auth_admin_login
@auth_amdin_role
def putAdminMusicInfo():
    return admin_works_api.putUploadMusicInfo()


@admin_works.route(f"{url}/admin/music/rank", methods=["PUT"])
@auth_admin_login
def putAdminMusicRank():
    return admin_works_api.putMusicRank()


@admin_works.route(f"{url}/admin/music", methods=["GET"])
@auth_admin_login
def getAdminMusicInfo():
    return admin_works_api.getMusicList()


@admin_works.route(f"{url}/admin/music/category", methods=["GET"])
@auth_admin_login
def getAdminMusicCategoryList():
    return admin_works_api.getMusicCategoryList()


@admin_works.route(f"{url}/admin/music/category", methods=["POST"])
@auth_admin_login
def postAdminMusicCategoryList():
    return admin_works_api.postMusicCategory()


@admin_works.route(f"{url}/admin/music/category", methods=["PUT"])
@auth_admin_login
def putAdminMusicCategoryList():
    return admin_works_api.putMusicCategory()


@admin_works.route(f"{url}/admin/music/category", methods=["DELETE"])
@auth_admin_login
def deleteAdminMusicCategoryList():
    return admin_works_api.deleteMusicCategory()


@admin_works.route(f"{url}/admin/template/category", methods=["GET"])
@auth_admin_login
def getAdminTemplateCategoryList():
    return admin_works_api.getTemplateCategoryList()


@admin_works.route(f"{url}/admin/template/category", methods=["POST"])
@auth_admin_login
def postAdminTemplateCategoryList():
    return admin_works_api.postTemplateCategory()


@admin_works.route(f"{url}/admin/template/category", methods=["PUT"])
@auth_admin_login
def putAdminTemplateCategoryList():
    return admin_works_api.putTemplateCategory()


@admin_works.route(f"{url}/admin/template/category", methods=["DELETE"])
@auth_admin_login
def deleteAdminTemplateCategoryList():
    return admin_works_api.deleteTemplateCategory()
