# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 16:53
@Auth: money
@File: route
"""
from flask import Blueprint
from middleware.auth import auth_user_login
from controller.apps.list import app_list_api

url = "/api/v1"
apps_list = Blueprint("apps_list", __name__, url_prefix="")


# 轮播图接口
@apps_list.route(f"{url}/banner", methods=["GET"])
def get_banner():
    return app_list_api.get_banner()


@apps_list.route(f"{url}/app/version", methods=["GET"])
def get_app_version():
    return app_list_api.get_version_number()


# 发现页推荐池优先作品接口
@apps_list.route(f"{url}/total/recommend/priority", methods=["GET"])
@auth_user_login
def total_recommend_works_priority():
    return app_list_api.get_total_recomm_pool_works_priority()


# 发现页推荐池普通作品接口
@apps_list.route(f"{url}/total/recommend/common", methods=["GET"])
@auth_user_login
def total_recommend_works_common():
    return app_list_api.get_total_recomm_pool_works_nopriority()


# 发现页未推荐中作品中新发布作品接口
@apps_list.route(f"{url}/total/norecommend/new", methods=["GET"])
@auth_user_login
def total_norecommend_new_works():
    return app_list_api.get_total_new_norecomm_works()


# 发现页未推荐中作品中之前发布作品接口
@apps_list.route(f"{url}/total/norecommend/old", methods=["GET"])
@auth_user_login
def total_norecommend_ole_works():
    return app_list_api.get_total_old_norecomm_works()


# 关注列表页接口
@apps_list.route(f"{url}/follow/dynamic/list", methods=["GET"])
@auth_user_login
def follow_dynamic_list():
    return app_list_api.get_user_follow_author_works_list()


# 关注列表页随机作者接口
@apps_list.route(f"{url}/random/author/list", methods=["GET"])
@auth_user_login
def random_author_list():
    return app_list_api.get_random_author_list()


# 摄影列表接口
@apps_list.route(f"{url}/pic/list", methods=["GET"])
@auth_user_login
def pic_list():
    return app_list_api.get_pic_list()


# 图集详情页接口
@apps_list.route(f"{url}/atlas/detail", methods=["GET"])
@auth_user_login
def pic_detail():
    return app_list_api.get_pic_detail()


# 影集详情页接口
@apps_list.route(f"{url}/video/detail", methods=["GET"])
@auth_user_login
def video_detail():
    return app_list_api.get_video_detail()


# 图文详情页列表接口
@apps_list.route(f"{url}/article/detail", methods=["GET"])
@auth_user_login
def article_detail():
    return app_list_api.get_article_detail()


# 摄影栏目标签接口
@apps_list.route(f"{url}/label_kw", methods=["GET"])
@auth_user_login
def photo_label():
    return app_list_api.get_label_list()


# 热搜词接口
@apps_list.route(f"{url}/hot/keyword", methods=["GET"])
def hot_keyword():
    return app_list_api.get_hot_keyword()


# 搜索关键词接口
@apps_list.route(f"{url}/search/keyword", methods=["GET"])
@auth_user_login
def search_keyword():
    return app_list_api.get_search_keyword()


# 搜索作品接口
@apps_list.route(f"{url}/search/works", methods=["GET"])
@auth_user_login
def search_works():
    return app_list_api.get_search_works()


# 搜索作者接口
@apps_list.route(f"{url}/search/author", methods=["GET"])
@auth_user_login
def search_author():
    return app_list_api.get_search_author()


# 拉黑用户或作品接口
@apps_list.route(f"{url}/blacklist", methods=["POST"])
@auth_user_login
def user_blacklist():
    return app_list_api.post_blacklist()


# 作品举报接口
@apps_list.route(f"{url}/works/report", methods=["POST"])
def works_report():
    return app_list_api.post_report_works()


# 作品点赞接口
@apps_list.route(f"{url}/works/like", methods=["POST"])
@auth_user_login
def works_like():
    return app_list_api.post_works_like()


# 评论列表接口
@apps_list.route(f"{url}/comment/list", methods=["GET"])
@auth_user_login
def comment_list():
    return app_list_api.get_comment_list()


# 作品评论点赞接口
@apps_list.route(f"{url}/comment/like", methods=["POST"])
@auth_user_login
def works_comment_like():
    return app_list_api.post_comment_like()


# 作品评论删除接口
@apps_list.route(f"{url}/comment/delete", methods=["PUT"])
@auth_user_login
def works_comment_delete():
    return app_list_api.put_delete_comment()


# 作品评论举报接口
@apps_list.route(f"{url}/comment/report", methods=["POST"])
@auth_user_login
def works_comment_report():
    return app_list_api.post_comment_report()


# 作者关注接口
@apps_list.route(f"{url}/author/follow", methods=["POST"])
@auth_user_login
def author_follow():
    return app_list_api.post_follow_user()


# 自定义供选标签接口
@apps_list.route(f"{url}/custom/label/option", methods=["GET"])
def custom_label_option():
    return app_list_api.get_option_label()


# 自定义标签接口
@apps_list.route(f"{url}/custom/label", methods=["POST"])
@auth_user_login
def custom_label():
    return app_list_api.post_custom_label()


# 版权说明接口
@apps_list.route(f"{url}/copyright", methods=["GET"])
def document_copyright():
    return app_list_api.get_copyright()


# 作品分享推荐接口
@apps_list.route(f"{url}/share/recomm/list", methods=["GET"])
@auth_user_login
def works_share_recomm_list():
    return app_list_api.get_share_recommend_works_list()


# 浏览记录
@apps_list.route(f"{url}/browse/add", methods=["POST"])
@auth_user_login
def works_browse_add():
    return app_list_api.post_works_browse_records()


# 对外提供获取token的接口
@apps_list.route(f"{url}/token", methods=["GET"])
def getToken():
    return app_list_api.getToken()


# 过审状态查询接口
@apps_list.route(f"{url}/audit", methods=["GET"])
def getAuditStatus():
    return app_list_api.getAuditStatus()


# 修改过审状态接口
@apps_list.route(f"{url}/audit", methods=["PUT"])
def putAuditStatus():
    return app_list_api.putAuditStatus()
