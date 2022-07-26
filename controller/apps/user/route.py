# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 16:55
@Auth: money
@File: route
"""
from flask import Blueprint
from flask import make_response
from flask import jsonify

from middleware.auth import auth_user_login
from controller.apps.user import app_user_api

url = "/api/v1"
apps_user = Blueprint("apps_user", __name__, url_prefix="")


@apps_user.before_request
@auth_user_login
def userInfoFilter():
    status, msg = app_user_api.userInfofilter()
    if status:
        pass
    else:
        return make_response(jsonify({"data": None, "code": 1, "msg": msg}), 400)


# 我的消息接口
@apps_user.route(f"{url}/user/message", methods=["GET"])
def user_message():
    return app_user_api.get_user_message()


# 删除我的消息接口
@apps_user.route(f"{url}/user/message/alter", methods=["PUT"])
def user_message_alter():
    return app_user_api.put_user_message_alter()


# 我的关注搜索接口
@apps_user.route(f"{url}/user/follow/search", methods=["GET"])
def user_follow_search():
    return app_user_api.get_user_follow_search()


# 我的关注取消接口
@apps_user.route(f"{url}/user/follow/cancel", methods=["PUT"])
def user_follow_cancel():
    return app_user_api.put_user_follow_state()


# 我的关注作品最新动态接口
@apps_user.route(f"{url}/user/follow/news", methods=["GET"])
def user_follow_news():
    return app_user_api.get_user_follow_works()


# 用户基本信息接口
@apps_user.route(f"{url}/user/info", methods=["GET"])
def user_info():
    return app_user_api.get_userinfo()


# 用户推荐兴趣标签接口
@apps_user.route(f"{url}/user/interest", methods=["GET"])
def user_interest_label():
    return app_user_api.get_user_interest_label()


# 用户更换头像接口
@apps_user.route(f"{url}/user/head/update", methods=["PUT"])
def user_head_img_update():
    return app_user_api.put_user_head_img()


# 用户更新背景图接口
@apps_user.route(f"{url}/user/background/update", methods=["PUT"])
def user_background_img_update():
    return app_user_api.put_user_background_img()


# 修改基本信息接口
@apps_user.route(f"{url}/user/info/alter", methods=["PUT"])
def user_info_alter():
    return app_user_api.put_alter_userinfo()


# 修改密码接口
@apps_user.route(f"{url}/user/alter/password", methods=["PUT"])
def user_info_alter_password():
    return app_user_api.post_userinfo_alter_pwd()


# 修改手机接口
@apps_user.route(f"{url}/user/alter/mobile", methods=["PUT"])
def user_info_alter_mobile():
    return app_user_api.post_userinfo_alter_mobile()


# 用户销售记录接口
@apps_user.route(f"{url}/user/sales/record", methods=["GET"])
def user_sales_record():
    return app_user_api.get_user_sales_records()


# 用户商品概况接口
@apps_user.route(f"{url}/user/data/statistic", methods=["GET"])
def user_data_statistic():
    return app_user_api.get_user_data_statistic()


# 提现银行接口
@apps_user.route(f"{url}/withdrawal/bank", methods=["GET"])
def withdrawal_bank_show():
    return app_user_api.get_user_withdrawal_bank()


# 用户账户余额接口
@apps_user.route(f"{url}/user/balance", methods=["GET"])
def user_balance():
    return app_user_api.get_user_balance()


# 用户提现申请接口
@apps_user.route(f"{url}/user/withdrawal", methods=["POST"])
def user_withdrawal_apply():
    return app_user_api.post_withdrawal_apply()


# 用户主页接口
@apps_user.route(f"{url}/user/home/page", methods=["GET"])
def user_home_page():
    return app_user_api.get_user_home_page()


# 用户关注列表接口
@apps_user.route(f"{url}/user/follow/list", methods=["GET"])
def user_follow_list():
    return app_user_api.get_user_follow_list()


# 用户粉丝列表接口
@apps_user.route(f"{url}/user/fans/list", methods=["GET"])
def user_fans_list():
    return app_user_api.get_user_fans_list()


# 我的作品管理接口
@apps_user.route(f"{url}/user/works/manage", methods=["GET"])
def user_works_manage():
    return app_user_api.get_works_manage()


# 我的评论历史记录接口
@apps_user.route(f"{url}/user/history/comment", methods=["GET"])
def user_history_comment():
    return app_user_api.get_user_comment_history()


# 我的点赞历史记录接口
@apps_user.route(f"{url}/user/history/like", methods=["GET"])
def user_history_comment_like():
    return app_user_api.get_user_like_history()


# 摄影师认证接口
@apps_user.route(f"{url}/cameraman/auth", methods=["POST"])
def area_auth_cameraman():
    return app_user_api.post_user_auth_cameraman()


# 用户已读消息接口
@apps_user.route(f"{url}/user/message/read", methods=["GET"])
def user_message_read():
    return app_user_api.put_user_message_state()


# 余额记录变更类别
@apps_user.route(f"{url}/user/balance/category", methods=["GET"])
def userBalanceChangeRecordsCategory():
    return app_user_api.getBalanceChangeRecordsCategory()


# 余额记录查询
@apps_user.route(f"{url}/user/balance/list", methods=["GET"])
def userBalanceChangeRecordsList():
    return app_user_api.balanceChangeRecords()


@apps_user.route(f"{url}/user/mobile/bind", methods=["POST"])
def userMobileAndPasswordBind():
    return app_user_api.bindUserMobileAndPassword()


@apps_user.route(f"{url}/user/password/bind", methods=["POST"])
def userPasswordBind():
    return app_user_api.bindUserPassword()
