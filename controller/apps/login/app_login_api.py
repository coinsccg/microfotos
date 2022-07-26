# -*- coding: utf-8 -*-
"""
@Time: 2020-06-30
@File: app_login_api
@Author: money 
"""
import re
import string
import time
import random
import datetime
import hashlib
import base64
from flask import request
from flask import g
from middleware.auth import response
from middleware.auth import generateJWT
from utils.util import generate_uid
from utils.tencent_sms import tencent_sms
from libs.captcha import captcha
from constant import constant
from initialize import log
from initialize import client
from model.app import User
from model.app import UserStatistical
from controller.apps.login.register_filter import RegisterFilter
from controller.apps.login.one_click_login import OneClickLogin
from dao.app.user.user import getUserInfo


def get_captcha():
    """获取图片码"""
    data = {}
    try:
        # 生成图片唯一id
        str_items = string.ascii_letters
        str_random = random.choice(str_items) + f"{int(time.time() * 1000)}"
        uid = hashlib.md5(str_random.encode()).hexdigest()
        # 获取图片验证码
        name, text, image = captcha.captcha.generate_captcha()

        # 图片验证码写入数据库
        condition = {
            "uid": uid, "type": "pic", "code": text, "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        client["verify"].insert_one(condition)

        # 响应base64格式的图片验证码
        pic_b64 = "data:image/jpg;base64," + base64.b64encode(image).decode()
        # resp = make_response(image)
        # resp.headers["Content-Type"] = "image/jpg"
        data["uid"] = uid
        data["pic"] = pic_b64
        return response(data=data)

    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_sms_code():
    """发送短信"""
    try:
        # 获取参数
        uid = request.json.get("uid")
        mobile = request.json.get("mobile")
        pic_code = request.json.get("pic_code")

        # 判断参数是否为空
        error = None
        if not uid:
            return response(msg="uid is required", code=1, status=400)
        if not mobile:
            error = "请输入手机号"
        elif not pic_code:
            error = "请输入图片验证码"
        elif len(str(mobile)) != 11 or not re.match(r"1[35678]\d{9}", str(mobile)):
            error = "请输入正确的手机号"
        if error is not None:
            return response(msg="请输入正确的手机号", code=1)

        # 验证图片验证码
        doc = client["verify"].find_one({"uid": str(uid)})
        if doc["code"].lower() != pic_code.lower():
            return response(msg="手机号或图片验证码错误", code=1)

        # 生成随机验证码并入库
        sms_code = "%06d" % random.randint(0, 999999)
        # sms_code = 1111
        condition = {
            "uid": str(mobile), "type": "sms", "code": str(sms_code), "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        client["verify"].insert_one(condition)

        # 调用第三方短信接口
        tencent_sms(str(mobile), str(sms_code))
        resp = response(msg="Send successfully.")
        return resp
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_sms_verify():
    """短信校验"""
    try:
        # 获取参数
        mobile = request.json.get("mobile")
        sms_code = request.json.get("sms_code")

        # 参数校验
        error = None
        if not mobile:
            error = "请输入手机号"
        elif not sms_code:
            error = "请输入短信验证码"
        elif len(str(mobile)) != 11 or not re.match(r"1[35678]\d{9}", str(mobile)):
            error = "请输入正确的手机号"
        if error is not None:
            return response(msg=error, code=1)

        # 验证短信验证码
        verify_doc = client["verify"].find_one({"uid": str(mobile), "type": "sms", "code": str(sms_code)})
        if not verify_doc:
            return response(msg="手机号或短信验证码错误", code=1)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_register():
    """
    用户注册
    """
    try:
        mobile = request.json.get("mobile")
        password = request.json.get("password")
        oauth = request.json.get("oauth")

        # 参数校验
        error = None
        if not mobile:
            error = "请输入手机号"
        elif not password:
            error = "请输入密码"
        elif len(password) > constant.PASSWORD_MAX:
            error = "密码长度上限{}".format(constant.PASSWORD_MAX)
        if error is not None:
            return response(msg=error, code=1)

        # 检查手机号是否重复注册
        doc = client["user"].find_one({"mobile": str(mobile)})
        if doc and oauth is None:
            return response(msg="手机号已被注册", code=1)

        # 生成用户唯一id
        uid = generate_uid(16)
        # 密码加密
        nick = None
        if oauth:
            if oauth["platform"] == "qq":
                nick = oauth["nickname"]
            else:
                nick = oauth["nickname"]
        passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()
        user = User()
        user.uid = uid
        user.nick = nick or "用户" + str(int(time.time()))[2:]
        user.sex = "保密"
        user.age = 18
        user.mobile = str(mobile)
        user.password = passwordMd5
        user.head_img_url = ""
        user.background_url = ""
        user.sign = "欢迎使用微图，快来更新您的签名吧!"
        user.state = 1
        user.account = str(mobile)
        user.auth = 0
        user.type = "user"
        user.balance = float(0)
        user.works_num = 0
        user.group = "comm"
        user.label = []
        user.recommend = -1
        user.create_time = int(time.time() * 1000)
        user.update_time = int(time.time() * 1000)
        user.login_time = int(time.time() * 1000)

        # 普通注册
        if not oauth:
            client["user"].insert_one(user.__dict__)
        # 第三方注册
        else:
            user.oauth = {"%s" % oauth["platform"]: oauth}
            client["user"].insert_one(user.__dict__)

        # 统计注册量
        todayTimestamp = int(time.mktime(datetime.date.today().timetuple()) * 1000)
        userStatisticalDoc = client["user_statistical"].update_one(
            {"user_id": uid, "date": todayTimestamp},
            {"$inc": {"register_num": 1}}
        )
        if userStatisticalDoc.modified_count == 0:
            userStatistical = UserStatistical()
            userStatistical.user_id = uid
            userStatistical.date = todayTimestamp
            userStatistical.works_num = 0
            userStatistical.sale_num = 0
            userStatistical.browse_num = 0
            userStatistical.like_num = 0
            userStatistical.goods_num = 0
            userStatistical.register_num = 1
            userStatistical.comment_num = 0
            userStatistical.comment_num = 0
            userStatistical.share_num = 0
            userStatistical.amount = float(0)
            userStatistical.create_time = int(time.time() * 1000)
            userStatistical.update_time = int(time.time() * 1000)

            client["user_statistical"].insert(userStatistical.__dict__)

        # 生成jwt
        token = generateJWT(uid)
        resp = response(msg="Request Successful")
        resp.headers["token"] = token
        return resp
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_account_login():
    """
    账户登录
    """
    try:
        mobile = request.json.get("mobile")
        password = request.json.get("password")

        # 校验
        error = None
        if not mobile:
            error = "请输入手机号"
        elif not password:
            error = "请输入密码"

        if error:
            return response(msg=error, code=1)

        # 用户密码检验
        passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()
        doc = client["user"].find_one({"mobile": str(mobile), "password": passwordMd5, "state": {"$in": [0, 1, 2]}})
        if not doc:
            return response(msg="用户名或密码错误", code=1)

        # 检查用户状态
        if doc["state"] == 0:
            return response(msg="您的账户已被冻结", code=1)

        # 生成jwt
        token = generateJWT(doc.get("uid"))

        # 记录登录时间
        client["user"].update_one({"uid": doc["uid"]}, {"$set": {"login_time": int(time.time() * 1000)}})

        resp = response(msg="Login successful.")
        resp.headers["token"] = token
        return resp
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_mobile_login():
    """手机登录"""
    try:

        mobile = request.json.get("mobile")
        sms_code = request.json.get("sms_code")

        # 校验
        error = None
        if not mobile:
            error = "请输入手机号"
        elif not sms_code:
            error = "请输入验证码"

        if error:
            return response(msg=error, code=1)

        # 验证短信验证码
        verify_doc = client["verify"].find_one({"uid": str(mobile), "type": "sms", "code": str(sms_code)})
        if not verify_doc:
            return response(msg="手机号或短信验证码错误", code=1)

        # 检验账户是否存在
        doc = client["user"].find_one({"mobile": str(mobile), "state": {"$in": [0, 1, 2]}}, {"uid": 1, "state": 1})
        if not doc:
            # 用户不存在注册用户
            uid = generate_uid(16)
            user = User()
            user.uid = uid
            user.nick = "用户" + str(int(time.time()))[2:]
            user.sex = "保密"
            user.age = 18
            user.mobile = mobile
            user.password = ""
            user.head_img_url = ""
            user.background_url = ""
            user.sign = "欢迎使用微图，快来更新您的签名吧!"
            user.state = 1
            user.account = mobile
            user.auth = 0
            user.type = "user"
            user.balance = float(0)
            user.works_num = 0
            user.group = "comm"
            user.label = []
            user.recommend = -1
            user.create_time = int(time.time() * 1000)
            user.update_time = int(time.time() * 1000)
            user.login_time = int(time.time() * 1000)
            client["user"].insert_one(user.__dict__)
        # 检查用户状态
        elif doc["state"] == 0:
            return response(msg="您的账户已被冻结", code=1)
        else:
            # 记录登录时间
            uid = doc.get("uid")
            client["user"].update_one({"uid": uid}, {"$set": {"login_time": int(time.time() * 1000)}})

        # 生成jwt
        token = generateJWT(uid)

        resp = response(msg="Login successful.")
        resp.headers["token"] = token
        return resp
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_oauth_bind():
    """
    第三方绑定
    """
    try:
        mobile = request.json.get("mobile")
        oauth = request.json.get("oauth")

        # 参数校验
        if not oauth:
            return response("oauth is required", code=1, status=400)

        # 进入绑定接口只有两种情况：1.账号存在绑定第三方账号; 2.账号不存在注册并绑定第三方账号
        if mobile:
            tmp = client["user"].find_one({"mobile": mobile, "state": 1}, {"uid": 1, "oauth": 1, "state": 1})
            if tmp is not None:
                # 检查账号是否被绑定及状态
                msg = None
                if tmp.get("oauth") is not None:
                    msg = "手机号已被绑定"
                elif tmp.get("state") == 0:
                    msg = "账号已被冻结"
                if msg is not None:
                    return response(msg=msg, code=1)

                # 账号绑定第三方账号
                platform = oauth['platform']
                client["user"].update_one(
                    {"mobile": mobile, "state": 1},
                    {"$set": {f"oauth.{platform}": oauth, "login_time": int(time.time() * 1000)}}
                )
                # 生成jwt
                token = generateJWT(tmp.get("uid"))
                resp = response(msg="绑定成功")
                resp.headers["token"] = token
                return resp

        # 1.没输入手机号，直接自动注册并绑定; 2.第一次第三方登录并直接绑定手机
        if oauth["platform"] == "qq":
            nick = oauth["nickname"]
        else:
            nick = oauth["nickname"]

        # 第三方头像过数美
        icon = oauth["icon"]
        registerFilter = RegisterFilter(nick, icon)
        headImgUrl = registerFilter.imageFilter()
        # 第三方昵称过数美
        nick = registerFilter.nickFilter()

        uid = generate_uid(16)
        user = User()
        user.uid = uid
        user.nick = nick[:10]
        user.sex = "保密"
        user.age = 18
        user.password = ""
        user.head_img_url = headImgUrl
        user.background_url = ""
        user.sign = "欢迎使用微图，快来更新您的签名吧!"
        user.state = 1
        user.account = mobile or ""
        user.auth = 0
        user.type = "user"
        user.balance = float(0)
        user.works_num = 0
        user.group = "comm"
        user.label = []
        user.recommend = -1
        user.oauth = {"%s" % oauth["platform"]: oauth}
        user.create_time = int(time.time() * 1000)
        user.update_time = int(time.time() * 1000)
        user.login_time = int(time.time() * 1000)

        if mobile is not None:
            user.mobile = mobile

        client["user"].insert_one(user.__dict__)
        # 生成jwt
        token = generateJWT(uid)
        resp = response(msg="Binding Success")
        resp.headers["token"] = token
        return resp
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_oauth_login():
    """第三方登录"""
    try:

        openid = request.json.get("userid")
        platform = request.json.get("platform")
        systemPlatform = request.json.get("system_platform")

        # 参数校验
        error = None
        if not openid:
            error = "openid is required"
        elif not platform:
            error = "platform is required"
        elif not systemPlatform:
            error = "systemPlatform is required"
        if error is not None:
            return response(msg=error, code=1, status=400)

        # 检查第三方账号是否已绑定账号
        if platform == "qq":
            condition1 = {"oauth.qq.uid": openid, "state": 1}
            condition2 = {"oauth.qq.userID": openid, "state": 1}
        else:
            condition1 = {"oauth.wechat.uid": openid, "state": 1}
            condition2 = {"oauth.wechat.userID": openid, "state": 1}
        userOne1 = client["user"].find_one(condition1, {"uid": 1, "state": 1})
        userOne2 = client["user"].find_one(condition2, {"uid": 1, "state": 1})
        userOne = userOne1 or userOne2
        if userOne is None:
            return response(data=1, msg="请绑定账号", code=1)

        # 检查账号状态
        if userOne["state"] == 0:
            return response(msg="账号已被冻结", code=1)

        userId = userOne.get("uid")
        token = generateJWT(userId)

        # 最新登录时间
        client["user"].update_one({"uid": userId}, {"$set": {"login_time": int(time.time() * 1000)}})
        resp = response()
        resp.headers["token"] = token
        return resp
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def get_user_logout():
    """退出登录"""
    try:
        # 用户登录状态判断
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1)
        return response(msg="退出成功")

    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def get_forgot_password():
    """忘记密码"""
    try:
        # 获取参数
        mobile = request.json.get("mobile")
        sms_code = request.json.get("sms_code")
        password = request.json.get("password")

        # 判断参数是否为空
        if not password:
            return response(msg="请输入密码", code=1)

        # 校验短信码
        doc = client["verify"].find_one({"uid": mobile, "type": "sms", "code": sms_code})
        if not doc:
            return response(msg="短信码或手机号错误", code=1)

        # 用户密码加密
        passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()

        # 更新密码
        client["user"].update_one({"mobile": mobile}, {"$set": {"password": passwordMd5}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_mobile_verify():
    """校验手机是否已经注册"""
    try:
        # 获取参数
        mobile = request.json.get("mobile")
        sms_code = request.json.get("sms_code")

        # 判断参数是否为空
        if not mobile:
            return response(msg="请输入手机号码", code=1)
        if not sms_code:
            return response(msg="请输入短信验证码", code=1)

        # 判断手机号长度
        if len(str(mobile)) != 11:
            return response(msg="请输入正确的手机号", code=1)

        # 判断手机格式
        if not re.match(r"1[35678]\d{9}", str(mobile)):
            return response(msg="请输入正确的手机号", code=1)

        # 验证短信验证码
        verify_doc = client["verify"].find_one({"uid": str(mobile), "type": "sms", "code": str(sms_code)})
        if not verify_doc:
            return response(msg="手机号或短信验证码错误", code=1)

        # 校验手机是否已经被注册
        doc = client["user"].find_one({"mobile": mobile})
        if doc:
            return response(msg="手机号已被注册", code=1)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def oneClickLogin():
    """手机账号一键登录"""
    loginToken = request.args.get("login_token")
    if not loginToken:
        return response(msg="login_token invalid", code=1, status=400)

    try:
        oneClickLogin = OneClickLogin(loginToken)
        mobile = oneClickLogin.main()
    except Exception as e:
        return response(msg="login_token parse failed, error: {}".format(e), code=1, status=400)

    # 检查手机号
    userInfo = getUserInfo(mobile)
    if userInfo:
        state = userInfo.get("state")
        uid = userInfo.get("uid")
        if state == 0:
            return response(msg="账号处于冻结状态，无法登录", code=1)
        else:
            token = generateJWT(uid)
            resp = response(msg="Login Success")
            resp.headers["token"] = token
            return resp
    else:
        # 新用户
        uid = generate_uid(16)
        user = User()
        user.uid = uid
        user.nick = "用户" + str(int(time.time()))[2:]
        user.sex = "保密"
        user.age = 18
        user.password = ""
        user.head_img_url = ""
        user.background_url = ""
        user.sign = "欢迎使用微图，快来更新您的签名吧!"
        user.state = 1
        user.account = mobile
        user.mobile = mobile
        user.auth = 0
        user.type = "user"
        user.balance = float(0)
        user.works_num = 0
        user.group = "comm"
        user.label = []
        user.recommend = -1
        user.create_time = int(time.time() * 1000)
        user.update_time = int(time.time() * 1000)
        user.login_time = int(time.time() * 1000)
        client["user"].insert_one(user.__dict__)
        # 生成jwt
        token = generateJWT(uid)
        resp = response(msg="Login Success")
        resp.headers["token"] = token
        return resp
