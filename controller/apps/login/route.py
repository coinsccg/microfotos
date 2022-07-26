# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 16:57
@Auth: money
@File: route
"""
from flask import Blueprint
from middleware.auth import auth_user_login
from controller.apps.login import app_login_api

url = "/api/v1"
apps_login = Blueprint("apps_login", __name__, url_prefix="")


# 图片验证码接口
@apps_login.route(f"{url}/captcha", methods=["GET"])
def pic_captcha():
    return app_login_api.get_captcha()


# 短信验证码接口
@apps_login.route(f"{url}/sms", methods=["POST"])
def sms_code():
    return app_login_api.post_sms_code()


# 短信验证码校验接口
@apps_login.route(f"{url}/sms/verify", methods=["POST"])
def sms_code_verify():
    return app_login_api.post_sms_verify()


# 校验手机号是否已被注册接口
@apps_login.route(f"{url}/mobile/verify", methods=["POST"])
def verify_mobile_is_register():
    return app_login_api.post_mobile_verify()


# 用户注册接口
@apps_login.route(f"{url}/register", methods=["POST"])
def user_register():
    return app_login_api.post_register()


# 账户登录接口
@apps_login.route(f"{url}/login/account", methods=["POST"])
def login_account():
    return app_login_api.post_account_login()


# 手机登录接口
@apps_login.route(f"{url}/login/mobile", methods=["POST"])
def login_mobile():
    return app_login_api.post_mobile_login()


# 第三方绑定接口
@apps_login.route(f"{url}/oauth/bind", methods=["POST"])
def oauth_bind():
    return app_login_api.post_oauth_bind()


# 第三方登录接口
@apps_login.route(f"{url}/oauth/login", methods=["POST"])
def oauth_login():
    return app_login_api.post_oauth_login()


# 退出接口
@apps_login.route(f"{url}/logout", methods=["GET"])
@auth_user_login
def user_logout():
    return app_login_api.get_user_logout()


# 一键登录
@apps_login.route(f"{url}/oneClickLogin", methods=["GET"])
def mobileOneClickLogin():
    return app_login_api.oneClickLogin()
