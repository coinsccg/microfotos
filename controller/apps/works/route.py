# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 16:56
@Auth: money
@File: route
"""
from flask import Blueprint
from flask import make_response
from flask import jsonify

from middleware.auth import auth_user_login
from controller.apps.works import app_works_api
from aop.aop import userForbiddenVerify

url = "/api/v1"
apps_works = Blueprint("apps_works", __name__, url_prefix="")


@apps_works.before_request
@auth_user_login
@userForbiddenVerify
def filterPic():
    status, msg = app_works_api.worksInfoAndPicfilter()
    if status:
        pass
    else:
        return make_response(jsonify({"data": None, "code": 1, "msg": msg}), 400)


# 素材上传通用接口（无水印接口）
@apps_works.route(f"{url}/user/upload/common", methods=["POST"])
def user_material_upload():
    return app_works_api.post_material_upload_common()


# 音频上传通用接口
@apps_works.route(f"{url}/user/audio/common", methods=["POST"])
def user_audio_upload():
    return app_works_api.post_audio_upload_common()


# 用户本地上传接口(有水印接口)
@apps_works.route(f"{url}/user/local/upload", methods=["POST"])
def user_local_upload():
    return app_works_api.post_pic_material_upload()


# 用户图片素材库列表接口
@apps_works.route(f"{url}/user/pic/material/list", methods=["GET"])
def user_pic_material_list():
    return app_works_api.get_pic_material()


# 用户历史标签接口
@apps_works.route(f"{url}/user/histroy/label", methods=["GET"])
def user_histroy_label():
    return app_works_api.get_user_history_label()


# 图集搜索标签接口
@apps_works.route(f"{url}/user/label/search", methods=["GET"])
def user_altas_label_searc():
    return app_works_api.get_altas_search_label()


# 创作图集-图片作品列表接口
@apps_works.route(f"{url}/pic/create/works/list", methods=["GET"])
def user_creation_atlas_pic_list():
    return app_works_api.get_user_pic_works_list()


# 创作图集作品接口
@apps_works.route(f"{url}/user/creation/atlas", methods=["POST"])
def user_creation_atlas_works():
    return app_works_api.post_pic_collect_works()


# 图集作品编辑接口
@apps_works.route(f"{url}/user/atlas/editor", methods=["PUT"])
def user_atlas_works_editor():
    return app_works_api.put_editor_pic_collect_works()


# 创作图文作品接口
@apps_works.route(f"{url}/user/creation/article", methods=["POST"])
def user_creation_article_works():
    return app_works_api.post_create_article_works()


# 图集创作页面详情接口
@apps_works.route(f"{url}/pic/creation/detail", methods=["GET"])
def pic_works_creation_detail():
    return app_works_api.get_pic_collect_create_api_detail()


# 影集搜索标签接口
@apps_works.route(f"{url}/video/label/search", methods=["GET"])
def user_video_label_search():
    return app_works_api.get_video_search_label()


# 用户添加标签接口
@apps_works.route(f"{url}/user/add/label", methods=["POST"])
def user_add_label():
    return app_works_api.post_user_add_label()


# 影集创作接口
@apps_works.route(f"{url}/user/video/create", methods=["POST"])
def user_video_works_create():
    return app_works_api.post_video_collect_works()


# 影集编辑接口
@apps_works.route(f"{url}/user/video/create", methods=["PUT"])
def user_video_works_editor():
    return app_works_api.put_eidtor_video_collect_works()


# 影集创作页面详情接口
@apps_works.route(f"{url}/video/creation/detail", methods=["GET"])
def video_works_creation_detail():
    return app_works_api.get_video_collect_create_api_detail()


# 图集、影集图片售卖接口
@apps_works.route(f"{url}/user/works/pic/sell", methods=["POST"])
def works_pic_sell():
    return app_works_api.post_altas_pic_sell()


# 图片规格信息接口
@apps_works.route(f"{url}/pic/spec", methods=["GET"])
def pic_spec_info():
    return app_works_api.get_pic_spec()


# 图集、影集图片列表信息接口
@apps_works.route(f"{url}/works/pic/list", methods=["GET"])
def works_pic_info():
    return app_works_api.get_works_pic_list()


# 影集图片压缩
@apps_works.route(f"{url}/user/pic/resize", methods=["POST"])
def picResize():
    return app_works_api.post_pic_resize()


# 我的商品列表接口
@apps_works.route(f"{url}/user/goods/list", methods=["GET"])
def user_goods_list():
    return app_works_api.get_user_goods_list()


# 删除图片商品接口
@apps_works.route(f"{url}/user/goods/state", methods=["PUT"])
def user_goods_state():
    return app_works_api.put_user_goods_state()


# 我的商品详情接口
@apps_works.route(f"{url}/user/goods/detail", methods=["GET"])
def user_goods_detail():
    return app_works_api.get_goods_detail()


# 我的素材库列表接口
@apps_works.route(f"{url}/user/material/list", methods=["GET"])
def user_info_material_list():
    return app_works_api.get_pic_material_list()


# 我的素材修改标题接口
@apps_works.route(f"{url}/user/material/title", methods=["PUT"])
def user_info_material_title():
    return app_works_api.put_pic_material_title()


# 我的素材修改标签接口
@apps_works.route(f"{url}/user/material/label", methods=["PUT"])
def user_info_material_label():
    return app_works_api.put_pic_material_label()


# 我的素材删除接口
@apps_works.route(f"{url}/user/material/state", methods=["PUT"])
def user_info_material_state():
    return app_works_api.put_pic_material_state()


# 我的素材上传接口
@apps_works.route(f"{url}/user/material/upload", methods=["POST"])
def user_info_material_upload():
    return app_works_api.post_pic_material_lib_upload()


# 我的音频素材列表接口
@apps_works.route(f"{url}/user/audio/list", methods=["GET"])
def user_info_audio_list():
    return app_works_api.get_audio_material_list()


# 我的音频素材修改标题接口
@apps_works.route(f"{url}/user/audio/title", methods=["PUT"])
def user_info_audio_title():
    return app_works_api.put_audio_material_title()


# 我的音频苏词啊修改标题接口
@apps_works.route(f"{url}/user/audio/label", methods=["PUT"])
def user_info_audio_label():
    return app_works_api.put_audio_material_label()


# 删除音频素材接口
@apps_works.route(f"{url}/user/audio/state", methods=["PUT"])
def user_info_audio_state():
    return app_works_api.put_audio_material_state()


# 上传音频素材接口
@apps_works.route(f"{url}/user/audio/upload", methods=["POST"])
def user_info_audio_upload():
    return app_works_api.post_audio_material_upload_pic()


# 图集、影集作品列表接口
@apps_works.route(f"{url}/user/works/list", methods=["GET"])
def user_info_works_list():
    return app_works_api.get_pic_video_wokrs_list()


# 删除作品
@apps_works.route(f"{url}/user/works/delete", methods=["PUT"])
def user_info_works_delete():
    return app_works_api.put_pic_works_state()


# 肖像权详情接口
@apps_works.route(f"{url}/user/portrait/detail", methods=["GET"])
def user_portrait_detail():
    return app_works_api.get_pic_portrait_detail()


# 肖像权编辑接口
@apps_works.route(f"{url}/user/portrait/editor", methods=["PUT"])
def user_portrait_editor():
    return app_works_api.put_pic_portrait_editor()


# 物产权详情接口
@apps_works.route(f"{url}/user/property/detail", methods=["GET"])
def user_property_detail():
    return app_works_api.get_pic_products_detail()


# 物产权编辑接口
@apps_works.route(f"{url}/user/property/editor", methods=["PUT"])
def user_property_editor():
    return app_works_api.put_pic_property_editor()


# 图片售卖申请
@apps_works.route(f"{url}/user/works/apply", methods=["POST"])
def pic_works_sell_apply():
    return app_works_api.post_pic_works_sell_apply()


# 图片售卖信息编辑接口
@apps_works.route(f"{url}/user/works/pic/editor", methods=["PUT"])
def pic_works_sell_info_editor():
    return app_works_api.put_pic_works_sell_info_editor()


# 图片售卖信息详情
@apps_works.route(f"{url}/user/works/pic/detail", methods=["GET"])
def pic_works_sell_info_detail():
    return app_works_api.get_pic_works_sell_info_detail()


# 图文作品列表接口
@apps_works.route(f"{url}/user/works/article", methods=["GET"])
def user_works_article():
    return app_works_api.get_article_wokrs_list()


# 作品发布审核接口
@apps_works.route(f"{url}/user/works/batch", methods=["POST"])
def user_works_release_apply():
    return app_works_api.put_works_release_apply()


# 区域地址接口
@apps_works.route(f"{url}/area", methods=["GET"])
def area_list():
    return app_works_api.get_area_list()


# 作品公开取消公开接口
@apps_works.route(f"{url}/user/works/release/state", methods=["PUT"])
def works_release_state():
    return app_works_api.put_works_release_state()


# 个人中心、素材数量统计接口
@apps_works.route(f"{url}/user/works/number/statistical", methods=["GET"])
def user_info_works_num_statistical():
    return app_works_api.get_works_num_statistical()


# 作品分享接口
@apps_works.route(f"{url}/works/share", methods=["POST"])
def user_works_share():
    return app_works_api.post_share_works()


# 用户协议接口
@apps_works.route(f"{url}/user/agreement/user", methods=["GET"])
def user_agreement():
    return app_works_api.get_user_agreement()


# 肖像协议接口
@apps_works.route(f"{url}/user/agreement/portrait", methods=["GET"])
def user_portrait_agreement():
    return app_works_api.get_portrait_agreement()


# 物产协议接口
@apps_works.route(f"{url}/user/agreement/product", methods=["GET"])
def user_product_agreement():
    return app_works_api.get_product_agreement()


# 隐私协议协议接口
@apps_works.route(f"{url}/user/agreement/private", methods=["GET"])
def user_private_agreement():
    return app_works_api.get_private_agreement()


# 授权合同接口
@apps_works.route(f"{url}/user/agreement/authorized", methods=["GET"])
def user_authorized_contract():
    return app_works_api.get_download_authorized_contract()


# 作品评论记录接口
@apps_works.route(f"{url}/works/comment", methods=["POST"])
def works_comment():
    return app_works_api.post_comment_records()


@apps_works.route(f"{url}/chunk/upload/init", methods=["GET"])
def videoUploadInit():
    return app_works_api.articleVideoUploadInit()


@apps_works.route(f"{url}/chunk/upload", methods=["POST"])
def VideoChunkUpload():
    return app_works_api.articleVideoUpload()


@apps_works.route(f"{url}/music", methods=["GET"])
def getMusicList():
    return app_works_api.getMusicList()
