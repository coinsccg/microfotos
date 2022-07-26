# -*- coding: utf-8 -*-
"""
@File: app_user_api
@Time: 2020-07-12 16:31:01
@Auth: money
"""
import random
import re
import time
import datetime
import base64
import hashlib
from bson.son import SON
from flask import request
from flask import g

from middleware.auth import response, verifyJWT
from utils.util import IdCardAuth
from constant import constant
from controller.apps.works.app_works_api import pic_upload_api
from initialize import log
from initialize import client
from dao.app.user import account
from dao.app.user import user
from filter.pic import pic
from filter.user import user_info


def get_user_message():
    """我的消息"""
    try:

        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询数据
        pipeline = [
            {"$match": {"user_id": user_id, "state": {"$in": [0, 1]}}},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "state": 0}}
        ]
        cursor = client["message"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_message_alter():
    """删除我的消息"""
    try:

        user_id = g.user_data["user_id"]
        msg_uid = request.json.get("msg_uid")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not msg_uid:
            error = "MsgUID is required."

        if error:
            return response(msg=error, code=1, status=400)

        # 更改state为-1
        doc = client["message"].update({"uid": msg_uid, "user_id": user_id}, {"$set": {"state": -1}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Params 'msg_uid' is error.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_follow_search():
    """搜索我的关注"""
    try:

        user_id = g.user_data["user_id"]
        search_kw = request.args.get("search_kw")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."

        if error:
            return response(msg=error, code=1, status=400)

        if len(search_kw) > constant.SEARCH_MAX:
            return response(msg=f"搜索字数上限{constant.SEARCH_MAX}", code=1)

        # 查询数据
        dataList, error = user.queryUserOwnFollowList(user_id, search_kw)
        if error:
            raise Exception(error)

        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_follow_state():
    """取消关注"""
    try:

        user_id = g.user_data["user_id"]
        author_id = request.json.get("author_id", None)

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not author_id:
            error = "AuthorID is required."

        if error:
            return response(msg=error, code=1, status=400)

        # 更改state为-1
        client["follow"].update(
            {"user_id": author_id, "fans_id": user_id},
            {"$set": {"state": -1}}
        )  # 更新成功doc["n"] = 1, 失败doc["n"] = 0

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_follow_works():
    """
    我的关注作品动态
    """
    data = {}
    try:
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # 查询数据
        data, error = user.queryUserFollowDynimac(user_id)
        if error:
            raise Exception(error)
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_userinfo():
    """
    用户基本信息
    """

    try:

        user_id = g.user_data["user_id"]
        user_info = g.user_data["user_info"]
        author_id = request.args.get("author_id")

        if not any([user_id, author_id]):
            return response(msg="UserID is required.", code=1, status=400)

        if author_id:
            user_info, error = user.queryUserInfo(author_id, user_id)
            if error:
                raise Exception(error)

        # 计算注册时长
        register_time = user_info["create_time"]
        login_time = user_info["login_time"]
        delta_time = (login_time - register_time) // (24 * 3600 * 1000)
        user_info["day"] = delta_time

        # 数据查询
        orderCount, dynamicCount, commentNum, likeNum, fansNum, followNum, msgNum, unpaidNum, error = user.queryUserDataStatistics(
            author_id, user_id)
        if error:
            raise Exception(error)
        user_info["order_count"] = orderCount
        user_info["dynamic_count"] = dynamicCount
        user_info["comment_num"] = commentNum
        user_info["like_num"] = likeNum
        user_info["follow_num"] = followNum
        user_info["fans_num"] = fansNum
        user_info["msg_num"] = msgNum
        user_info["unpay_num"] = unpaidNum
        return response(data=user_info)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_interest_label():
    """用户推荐兴趣标签"""
    try:
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # cursor = client["interest_label"].find({}, {"_id": 0, "label": 1, "related": 1})
        pipeline = [
            {"$match": {"state": 2}},
            {"$sort": SON([("priority", -1)])},
            {"$limit": 100},
            {"$sample": {"size": 5}},
            {"$project": {"_id": 0, "label": 1}}
        ]
        cursor = client["label"].aggregate(pipeline)
        data_list = []
        for doc in cursor:
            data_list.append(doc.get("label"))
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_head_img():
    """修改用户头像"""
    try:
        # 用户id
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # data_list = pic_upload_api(user_id)
        data_list = g.data
        obj = data_list[0]
        head_img_url = obj.get("file_path")
        doc = client["user"].update({"uid": user_id}, {"$set": {"head_img_url": head_img_url}})
        if doc["n"] == 0:
            return response(msg="Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_background_img():
    """修改用户背景图"""
    try:
        # 用户id
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # data_list = pic_upload_api(user_id)
        data_list = g.data
        obj = data_list[0]
        background_img_url = obj.get("file_path")
        doc = client["user"].update({"uid": user_id}, {"$set": {"background_url": background_img_url}})
        if doc["n"] == 0:
            return response(msg="Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_alter_userinfo(nick_max=10, label_max=20, sign_max=30):
    """
    修改用户信息
    :param: nick_max: 昵称上限
    :param: label_max: 标签上限
    :param: sign_max: 签名上限
    """

    try:

        user_id = g.user_data["user_id"]
        user_info = request.get_json()  # nick昵称 sign签名 label标签 sex性别

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not user_info.keys():
            error = "The lack of field."
        if user_info.get("sex") and user_info.get("sex") not in ["男", "女", "保密"]:
            error = "Sex invalid."

        if error:
            return response(msg=error, code=1, status=400)

        if user_info.get("nick") and len(user_info.get("nick")) > nick_max:
            error = "昵称上限10个字符"
        elif user_info.get("nick"):
            # 过滤关键词
            for kw in constant.FILTER_KW:
                if user_info.get("nick").__contains__(kw):
                    error = "昵称中不能包含以下关键词：%s" % "、".join(constant.FILTER_KW)
        elif user_info.get("sign") and len(user_info.get("sign")) > sign_max:
            error = "签名上限60个字符"
        elif user_info.get("label") and len(user_info.get("label")) > label_max:
            error = "标签上限20个"

        if error:
            return response(msg=error, code=1)

        # 入库
        doc = client["user"].update({"uid": user_id}, {"$set": user_info})
        if doc["n"] == 0:
            return response(msg="Bad Request: Params 'user_id' is error.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_userinfo_alter_pwd():
    """个人中心-更改密码"""
    try:

        mobile = request.json.get("mobile")
        sms_code = request.json.get("sms_code")
        password = request.json.get("password")

        # 校验
        if not password:
            return response(msg="请输入密码", code=1)
        if len(password) > constant.PASSWORD_MAX:
            return response(msg=f"密码长度上限{constant.PASSWORD_MAX}", code=1)

        verifyDoc = client["verify"].find_one({"uid": mobile, "type": "sms", "code": sms_code})
        if not verifyDoc:
            return response(msg="短信码或手机号错误", code=1)

        # 用户密码加密
        passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()

        # 更新密码
        client["user"].update_one({"mobile": mobile}, {"$set": {"password": passwordMd5}})
        return response(status=200)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_userinfo_alter_mobile():
    """个人中心-更换手机"""
    try:
        # 用户登录状态判断
        uid = g.user_data["user_id"]
        if not uid:
            return response(msg="Bad Request: Token expired.", code=1, status=401)

        # 获取参数
        new_mobile = request.json.get("new_mobile")
        sms_code = request.json.get("sms_code")
        # 判断参数是否为空
        if not new_mobile:
            return response(msg="请输入手机号码", code=1)
        # 校验短信码
        doc = client["verify"].find_one({"uid": new_mobile, "type": "sms", "code": sms_code})
        if not doc:
            return response(msg="短信码或手机号错误", code=1)

        # 判断手机号长度
        if len(new_mobile) != 11:
            return response(msg="请输入正确的手机号", code=1)

        result, _ = user.getUserMobile(new_mobile)
        if result:
            return response(msg="手机号已被绑定", code=1)

        # 不能重复换绑同一个手机号
        doc = client["user"].find_one({"uid": uid})
        if doc.get("mobile"):
            if new_mobile == doc["mobile"]:
                return response(msg="不能换绑原手机号", code=1)

        # 判断手机格式
        if not re.match(r"1[35678]\d{9}", new_mobile):
            return response(msg="请输入正确的手机号", code=1)

        # 更新手机号
        client["user"].update_one({"uid": uid}, {"$set": {"mobile": new_mobile, "account": new_mobile}})

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def get_user_sales_records():
    """销售记录"""
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num", None)
        page = request.args.get("page", None)

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询数据
        dataList, error = account.queryWorksSaleRecords(user_id, page, num)
        if error:
            raise Exception(error)

        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_data_statistic():
    """商品概况"""
    try:
        # 用户id
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        # 查询数据
        dataList, error = account.queryWorksSallStatistical(user_id)
        if error:
            raise Exception(error)
        data = {
            "browse_num": 0, "comment_num": 0, "amount_num": float(0), "share_num": 0, "like_num": 0,
            "sale_num": 0
        }
        return response(data=dataList[0] if dataList else data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_withdrawal_bank():
    """提现银行"""
    try:

        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # 查询数据
        dataList, error = user.withdrawlBankList()
        if error:
            raise Exception(error)

        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_balance():
    """余额"""
    data = {}
    try:
        # 用户id
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # 当前与昨天时间
        today = datetime.datetime.now()
        date = today.strftime("%Y-%m-%d") + " 0{}:00:00".format(0)
        timeArray = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        yesterday_stamp = int(time.mktime((timeArray - datetime.timedelta(days=1)).timetuple())) * 1000

        # 查询
        balance, amount, fees, lock, error = user.balanceRelevant(user_id, yesterday_stamp)
        data["balance"] = round(balance, 2)
        data["amount"] = float(amount)
        data["fees"] = fees

        # 提现申请
        data["lock"] = float(lock)
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_withdrawal_apply():
    """提现申请"""
    try:
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        # 参数
        wd_way = request.json.get("wd_way")
        bank_id = request.json.get("bank_id")
        trade_name = request.json.get("trade_name")  # 提现账户名
        trade_id = request.json.get("trade_id")  # 提现账号
        amount = request.json.get("amount")
        amount = float(amount)

        # 校验
        error = None
        if not trade_name:
            error = "请填写账户名"
        elif not trade_id:
            error = "请填写账号"
        elif not amount:
            error = "请填写提现金额"
        elif amount < 0:
            error = "请填写正确的金额"

        if error:
            return response(msg=error, code=1)

        doc = client["user"].find_one({"uid": user_id})
        balance = doc["balance"]
        if amount > balance:
            return response(msg="余额不足", code=1)

        order = str(int(time.time() * 1000)) + str(random.randint(1001, 9999))
        if not wd_way:
            doc = client["bank"].find_one({"uid": bank_id})

            if not doc:
                return response(msg="Bad Request: Params 'bank_id' is error.", code=1, status=400)

        if wd_way and wd_way != "支付宝":
            return response(msg="Bad Request: Params 'wd_way' is error.", code=1, status=400)

        # 提现审核
        # cursor = client["bank"].find({"state": 1})
        # fees = [doc for doc in cursor][0]["fees"]
        # amount = amount * (1 - fees)
        condition = {
            "order": order, "channel": doc["name"] if not wd_way else wd_way, "user_id": user_id,
            "trade_name": trade_name, "trade_id": trade_id, "amount": amount, "state": 1,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }
        client["withdrawal_records"].insert(condition)

        # 提现余额记录
        tmp = {
            "user_id": user_id, "type": "提现冻结", "order": order, "amount": amount,
            "balance": balance, "state": 1, "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        client["balance_record"].insert(tmp)

        return response(msg="将在7-14个工作日到账，届时注意查收")
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_home_page():
    """用户主页"""
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")
        author_id = request.args.get("user_id")

        # 校验
        error = None
        if not any([user_id, author_id]):
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 用户作品
        dataList, error = user.queryUserWorksList(author_id if author_id else user_id, user_id, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_follow_list():
    """用户的关注列表"""
    try:

        user_id = g.user_data["user_id"]
        author_id = request.args.get("user_id")
        search_kw = request.args.get("search_kw")
        page = request.args.get("page")
        num = request.args.get("num")

        # 校验
        error = None
        if not author_id:
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)
        dataList, error = user.queryFollowList(user_id, author_id, search_kw, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error %s." % str(e), code=1, status=500)


def get_user_fans_list():
    """
    用户的粉丝列表
    """
    try:

        user_id = g.user_data["user_id"]
        author_id = request.args.get("user_id")
        page = request.args.get("page")
        num = request.args.get("num")

        # 校验
        error = None
        if not author_id:
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        dataList, error = user.queryFansList(user_id, author_id, page, num)
        if error:
            raise Exception(error)

        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error %s." % str(e), code=1, status=500)


def get_works_manage():
    """
    我的作品
    :param  domain: 域名
    """
    data = {}
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询数据
        dataList, error = user.queryUserWorksList(user_id, user_id, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_comment_history():
    """
    我的评论历史
    """
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")
        type = request.args.get("type")  # 我的评论1，收到的评论2

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif type not in ["1", "2"]:
            error = "Type invalid."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询数据
        dataList, error = user.queryCommentHistoryList(user_id, page, num, type)
        if error:
            raise Exception(error)

        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_like_history():
    """
    我的点赞历史
    """
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")
        type = request.args.get("type")  # 我的点赞1，收到的点赞2

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif type not in ["1", "2"]:
            error = "Type invalid."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询数据
        dataList, error = user.queryLikeHistoryList(user_id, page, num, type)
        if error:
            raise Exception(error)

        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_user_auth_cameraman(title_length_max=32, addr_length_max=128):
    """
    摄影师认证
    :param title_length_max: 标题上限
    :param addr_length_max: 地址上限
    """
    try:

        user_id = g.user_data["user_id"]
        auth = g.user_data["user_info"]["auth"]

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
            return response(msg=error, code=1, status=400)
        elif auth == 1:
            error = "您已提交认证申请，请耐心等待"
        elif auth == 2:
            error = "您已成功通过摄影师认证"

        if error:
            return response(msg=error, code=1)

        name = request.json.get("name")
        id_card = request.json.get("id_card")
        addr = request.json.get("addr")
        id_card_a_url = request.json.get("id_card_a_url")
        id_card_b_url = request.json.get("id_card_b_url")
        repre_works = request.json.get("repre_works")
        check = IdCardAuth()

        error = None
        if not name:
            error = "请输入姓名"
        elif len(name) > title_length_max:
            error = f"名字最长允许{title_length_max}个字符"
        elif not check.check_true(id_card):
            error = "请输入正确的身份证号"
        elif not addr:
            error = "请输入地址"
        elif len(addr) > addr_length_max:
            error = f"地址最长允许{addr_length_max}个字符"
        elif not all([id_card_b_url, id_card_a_url]):
            error = "请上传身份证正反两面"
        elif len(repre_works) < 5:
            error = "请上传至少五张代表作品"

        if error:
            return response(msg=error, code=1)

        id_card_a_url = id_card_a_url.replace(constant.DOMAIN, "")
        id_card_b_url = id_card_b_url.replace(constant.DOMAIN, "")
        temp_list = []
        for i in repre_works:
            pic = i.replace(constant.DOMAIN, "")
            temp_list.append(pic)
        # 入库
        error = user.authCamerman(name, id_card, id_card_a_url, id_card_b_url, temp_list, addr, user_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_message_state():
    """用户消息已读接口"""
    try:
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        client["message"].update({"user_id": user_id, "state": 1}, {"$set": {"state": 0}}, multi=True)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def getBalanceChangeRecordsCategory():
    """余额变更记录类别"""
    try:
        return response(data=constant.balanceChangeRecordsCategory)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def balanceChangeRecords():
    """余额变更记录"""
    try:
        userId = g.user_data["user_id"]
        category = request.args.get("category")  # all
        startTime = request.args.get("start_time")
        endTime = request.args.get("end_time")
        startAmount = request.args.get("start_amount")
        endAmount = request.args.get("end_amount")
        page = request.args.get("page")
        num = request.args.get("num")

        # 参数校验
        error = None
        if not userId:
            error = "user not logged"
        elif category != "all" and (category not in constant.balanceChangeRecordsCategory):
            error = "category invalid"
        elif not (startTime.isdigit() and endTime.isdigit()):
            error = "start_time or end_time invalid"
        elif int(startTime) > int(endTime):
            error = "start_time should less then end_time"
        elif not (page.isdigit() and num.isdigit()):
            error = "page or num invalid"
        elif (int(endTime) - int(startTime)) / (1000 * 3600 * 24) > 90:
            print((int(endTime) - int(startTime)) / (1000 * 3600 * 24))
            error = "the maximum query range is 90 days"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif int(num) > constant.numMax:
            error = "num max {}".format(constant.numMax)
        elif int(page) > constant.pageMax:
            error = "page max {}".format(constant.pageMax)
        if error:
            return response(msg=error, code=1, status=400)

        if any([startAmount, endAmount]):
            if startAmount and endAmount:
                try:
                    startAmount = float(startAmount)
                    endAmount = float(endAmount)
                except Exception as e:
                    error = "请输入正确的金额"
                if startAmount > endAmount:
                    error = "请输入正确的起始金额"
                if endAmount > constant.queryBalanceChangeRecordsAmountMax or startAmount > constant.queryBalanceChangeRecordsAmountMax:
                    error = "查询金额上限{}".format(constant.queryBalanceChangeRecordsAmountMax)
            else:
                tmp = None
                if startAmount:
                    tmp = startAmount
                if endAmount:
                    tmp = endAmount

                try:
                    tmp = float(tmp)
                except Exception as e:
                    error = "请输入正确的金额"
                if tmp > constant.queryBalanceChangeRecordsAmountMax:
                    error = "查询金额上限{}".format(constant.queryBalanceChangeRecordsAmountMax)

        if error:
            return response(msg=error, code=1)

        # 余额记录查询
        balanceRecordsList, error = account.queryBalanceChangeRecordsList(userId, category, int(startTime),
                                                                          int(endTime), startAmount, endAmount,
                                                                          int(page), int(num))
        if error:
            raise Exception(error)

        return response(data=balanceRecordsList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def bindUserMobileAndPassword():
    try:
        userId = g.user_data["user_id"]
        mobile = request.json.get("mobile")
        password = request.json.get("password")

        # 参数校验
        error = None
        if not userId:
            error = "user not logged in"
        elif len(str(mobile)) != 11:
            error = "mobile invalid"
        elif not re.match(r"1[35678]\d{9}", str(mobile)):
            error = "mobile invalid"
        elif not password:
            error = "password is required"
        if error is not None:
            return response(msg=error, code=1, status=400)
        if len(password) > constant.PASSWORD_MAX:
            return response(msg="密码长度上限{}".format(constant.PASSWORD_MAX), code=1)

        # 检查手机号是否已被绑定
        result, _ = user.getUserMobile(mobile)
        if result:
            return response(msg="手机号已被绑定", code=1)

        # 设置手机或密码
        passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()
        error = user.updateUserPasswordAndMobile(userId, mobile, passwordMd5)
        if error is not None:
            raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def bindUserPassword():
    try:
        userId = g.user_data["user_id"]
        password = request.json.get("password")

        # 参数校验
        error = None
        if not userId:
            error = "user not logged in"
        elif not password:
            error = "password is required"
        if error is not None:
            return response(msg=error, code=1, status=400)
        if len(password) > constant.PASSWORD_MAX:
            return response(msg="密码长度上限{}".format(constant.PASSWORD_MAX), code=1)

        # 设置手机或密码
        passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()
        error = user.updateUserPassword(userId, passwordMd5)
        if error is not None:
            raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def userInfofilter():
    user_id = g.user_data["user_id"]
    url = request.url

    if url.endswith("user/head/update"):  # 背景图过滤
        demo = pic.ImageFilter()
        token = request.headers.get("token")
        uid, result = verifyJWT(token)
        if not result:
            return True, None
        data, _ = pic_upload_api(uid)
        g.data = data  # 后续函数所需参数
        for i in data:
            rest, restMsg = demo.sendRequest("bgc", "001", constant.DOMAIN + i["file_path"])
            if rest:
                return True, None
            else:
                return False, "图片可能涉嫌：" + restMsg
        return True, None

    if url.endswith("user/background/update"):  # 头像过滤
        demo = pic.ImageFilter()
        token = request.headers.get("token")
        uid, result = verifyJWT(token)
        if not result:
            return True, None
        data, _ = pic_upload_api(uid)
        g.data = data  # 后续函数所需参数
        for i in data:
            rest, restMsg = demo.sendRequest("img", "001", constant.DOMAIN + i["file_path"])
            if rest:
                return True, None
            else:
                return False, "图片可能涉嫌：" + restMsg
        return True, None

    if url.endswith("user/info/alter"):  # 昵称、签名
        nick = request.json.get("nick")
        sign = request.json.get("sign")
        if nick:  # 昵称
            demo = user_info.UserInfoFilter()
            rest, restMsg = demo.sendRequest("nick", user_id, nick)
            if rest:
                return True, None
            else:
                return False, "用户昵称可能涉嫌：" + restMsg
        elif sign:  # 签名
            demo = user_info.UserInfoFilter()
            rest, restMsg = demo.sendRequest("sign", user_id, sign)
            if rest:
                return True, None
            else:
                return False, "用户签名可能涉嫌：" + restMsg

    return True, None
