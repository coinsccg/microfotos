# -*- coding: utf-8 -*-
"""
@Time: 2020/07/19 15:15:04
@File: admin_user_api.py
@Auth: money
"""
import re
import base64
import time
import random
import datetime
import json
import hashlib
from bson.son import SON
from flask import request
from middleware.auth import response
from utils.util import generate_uid
from constant import constant
from initialize import log
from initialize import client
from initialize import init_stamp
from controller.admin.comm import comm
from dao.admin.users import users


def get_user_filter_list():
    """
    用户列表筛选
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        category = request.args.get("category")  # 账号传account, 昵称传nick
        content = request.args.get("content")
        group = request.args.get("group")  # default全部 comm一般用户，auth认证摄影师
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        sort_way = request.args.get("sort_way")  # -1 倒序 1正序

        # 校验参数
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["account", "nick"]:
            error = "category invalid"
        elif sort_way not in ["-1", "1"]:
            error = "sort_way invalid"
        # elif not start_time:
        #     error = "start_time is required"
        # elif not end_time:
        #     error = "end_time is required"
        if error:
            return response(msg=error, code=1, status=400)

        startTime, endTime, deltaDay = comm.strDateToTimestamp(start_time, end_time)

        # if deltaDay > constant.queryDayCount:
        #     error = "查询时间范围仅限{}以内".format(constant.queryDayCount)
        if content and len(content) > constant.SEARCH_MAX:
            error = "搜索关键词最多{}个字符".format(constant.SEARCH_MAX)
        if error:
            return response(msg=error, code=1)

        # 查询
        pipeline = [
            {
                "$match": {
                    "type": "user", "state": {"$ne": -1},
                    "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                        "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None,
                    "group" if group != "default" else "null": group if group != "default" else None,
                    ("nick" if category == "nick" else "account") if content else "null": {
                        "$regex": content} if content else None
                }
            },
            {"$sort": SON([("create_time", int(sort_way)), ("mobile", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "nick": 1, "account": 1, "group": 1, "state": 1,
                    "head_img_url": {
                        "$cond": {
                            "if": {"$ne": ["$head_img_url", ""]},
                            "then": {"$concat": [constant.DOMAIN, "$head_img_url"]},
                            "else": "$head_img_url"
                        }
                    },
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    },
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        condition1 = {
            "type": "user", "state": {"$ne": -1},
            ("nick" if category == "nick" else "account") if content else "null": {
                "$regex": content} if content else None,
            "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None
        }
        condition2 = {
            "type": "user", "state": {"$ne": -1},
            "group": "comm", ("nick" if category == "nick" else "account") if content else "null": {
                "$regex": content} if content else None
        }
        condition3 = {
            "type": "user", "state": {"$ne": -1},
            "group": "auth", ("nick" if category == "nick" else "account") if content else "null": {
                "$regex": content} if content else None
        }
        count1 = client["user"].find(condition1).count()
        count2 = client["user"].find(condition2).count()
        count3 = client["user"].find(condition3).count()
        data["list"] = data_list if data_list else []
        data["count"] = count1
        data["comm"] = count2
        data["auth"] = count3

        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_state():
    """冻结、恢复用户"""
    try:
        # 参数
        user_id = request.json.get("user_id")  # array
        state = request.json.get("state")  # 冻结传0, 恢复传1
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if state not in [0, 1]:
            return response(msg="Bad Request: Params 'state' is error.", code=1, status=400)
        doc = client["user"].update({"uid": {"$in": user_id}}, {"$set": {"state": int(state)}}, multi=True)
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_group():
    """移动用户组"""
    try:
        # 参数
        user_id = request.json.get("user_id")  # array 
        group = request.json.get("group")  # comm一般用户，auth认证摄影师
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if group not in ["comm", "auth"]:
            return response(msg="Bad Request: Params 'group' is error.", code=1, status=400)
        for i in user_id:
            doc = client["user"].find_one({"uid": i})
            if doc["type"] == "org":
                if doc["belong"] != "master":
                    return response(msg="只有主账号才能移动组", code=1)
                temp = {"$set": {"group": group, "auth": 0}}
                if group == "auth":
                    temp = {"$set": {"group": group, "auth": 2}}
                client["user"].update(
                    {"org_name": doc["org_name"]},
                    temp,
                    multi=True
                )
            else:
                temp = {"$set": {"group": group, "auth": 0}}
                if group == "auth":
                    temp = {"$set": {"group": group, "auth": 2}}
                client["user"].update({"uid": i}, temp)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_detail(domain=constant.DOMAIN):
    """
    获取用户详情
    :param domain: 域名
    """
    try:
        # 参数
        user_id = request.args.get("user_id")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        # 基本信息查询
        pipeline = [
            {"$match": {"uid": user_id}},
            {
                "$project": {
                    "_id": 0, "uid": 1, "nick": 1, "balance": {"$ifNull": ["$balance", float(0)]}, "sign": 1,
                    "org_name": 1, "account": 1, "label": 1, "state": 1, "sex": 1, "group": 1, "mobile": 1,
                    "belong": 1,
                    "head_img_url": {
                        "$cond": {
                            "if": {"$ne": ["$head_img_url", ""]},
                            "then": {"$concat": [domain, "$head_img_url"]},
                            "else": "$head_img_url"
                        }
                    },
                    "background_url": {
                        "$cond": {
                            "if": {"$ne": ["$background_url", ""]},
                            "then": {"$concat": [domain, "$background_url"]},
                            "else": "$background_url"
                        }
                    },
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        if not data_list:
            return response(msg="Bad Request: Params 'user_id' is error.", code=1, status=400)
        doc = data_list[0]
        # 作品数量查询
        pipeline = [
            {"$match": {"user_id": user_id, "state": {"$ne": -1}}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
            {"$project": {"type": "$_id", "count": 1}}
        ]
        cursor = client["works"].aggregate(pipeline)
        pic_num = 0
        atlas_num = 0
        video_num = 0
        article_num = 0
        for i in cursor:
            if i.get("type") == "tp":
                pic_num = i.get("count")
            elif i.get("type") == "tj":
                atlas_num = i.get("count")
            elif i.get("type") == "yj":
                video_num = i.get("count")
            elif i.get("type") == "tw":
                article_num = i.get('count')
        doc["article_num"] = article_num
        doc["atlas_num"] = atlas_num + pic_num
        doc["video_num"] = video_num
        return response(data=doc)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_password():
    """重置用户密码"""
    try:
        # 参数
        user_id = request.json.get("user_id")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        # 密码加密
        password = "123456"
        password_b64 = base64.b64encode(password.encode()).decode()
        # 更新password
        doc = client["user"].update({"uid": user_id}, {"$set": {"password": password_b64}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_mobile():
    """修改用户手机"""
    try:
        # 参数
        user_id = request.json.get("user_id")
        mobile = request.json.get("mobile")

        # 参数校验
        error = None
        if not user_id:
            error = "userId is required"
        elif not mobile:
            error = "mobile is required"
        if error is not None:
            return response(msg=error, code=1, status=400)

        if len(str(mobile)) != 11:
            error = "请输入正确的手机号"
        elif not re.match(r"1[35678]\d{9}", str(mobile)):
            error = "请输入正确的手机号"
        if error is not None:
            return response(msg=error, code=1)

        # 判断手机号是否存在
        user = client["user"].find_one({"mobile": mobile, "state": {"$ne": -1}}, {"uid": 1})
        if user:
            return response(msg="手机号已存在", code=1)

        # 更新mobile
        doc = client["user"].update({"uid": user_id}, {"$set": {"mobile": mobile}})
        if doc["n"] == 0:
            return response(msg="userId is invalid", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_user_message():
    """给用户发送消息"""
    try:
        # 参数
        user_id = request.json.get("user_id")
        content = request.json.get("content")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if not content:
            return response(msg="请输入内容", code=1)
        if len(content) > 32:
            return response(msg="消息文字上限32个字符", code=1)
        uid = generate_uid(24)
        client["message"].insert(
            {
                "uid": uid, "user_id": user_id, "push_people": "系统消息", "desc": content, "type": 1,
                "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
        )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_balance_operation():
    """用户余额操作接口"""
    try:
        # 参数
        user_id = request.json.get("user_id")
        inc = request.json.get("inc")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if not inc:
            return response(msg="请输入充值金额", code=1)
        doc = client["user"].find_one({"uid": user_id})
        balance = doc["balance"]
        doc = client["user"].update({"uid": user_id}, {"$inc": {"balance": float(inc)}})
        if doc["n"] == 0:
            return response(msg="操作失败", code=1)
        # 记录操作记录
        stamp_time = int(time.time() * 1000)
        random_str = "%02d" % random.randint(0, 100)
        order = random_str + f"{stamp_time}"
        condition = {
            "user_id": user_id, "type": "后台充值" if float(inc) >= 0 else "后台扣除",
            "order": order, "amount": float(inc), "balance": float(inc) + balance, "state": 1,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }
        client["balance_record"].insert(condition)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_balance_records(delta_time=30):
    """
    用户余额记录表
    :param delta_time: 允许查询的最大区间30天
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        user_id = request.args.get("user_id")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if not start_time:
            return response(msg="Bad Request: Miss params: 'start_time'.", code=1, status=400)
        if not end_time:
            return response(msg="Bad Request: Miss params: 'end_time'.", code=1, status=400)
        temp_list = (int(end_time) - int(start_time)) // (24 * 3600 * 1000)
        if temp_list > delta_time:
            return response(msg=f"最大只能查询{delta_time}天以内的记录", code=1)
        pipeline = [
            {"$match": {"user_id": user_id, "state": 1, "$and": [{"create_time": {"$gte": int(start_time)}},
                                                                 {"create_time": {"$lte": int(end_time)}}]}},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "user_id": 1, "type": 1, "order": 1, "amount": 1, "balance": {"$round": ["$balance", 2]},
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["balance_record"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        condition = {
            "user_id": user_id, "state": 1,
            "$and": [
                {"create_time": {"$gte": int(start_time)}},
                {"create_time": {"$lte": int(end_time)}}
            ]
        }
        count = client["balance_record"].find(condition).count()
        data["count"] = count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_org_list():
    """机构列表"""
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        belong = request.args.get("belong")  # 全部传default, 主账号master, 子账号slave

        # 校验参数
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif belong not in ["default", "master", "slave"]:
            error = "belong invalid"
        if error:
            return response(msg=error, code=1, status=400)

        # 查询
        pipeline = [
            {
                "$match": {
                    "type": "org", "state": {"$ne": -1},
                    "belong": {"$in": ["master", "slave"]} if belong == "default" else {"$eq": belong},

                }
            },
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "org_name": 1, "belong": 1, "head_img_url": 1,
                    "nick": 1, "account": 1, "group": 1, "state": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        if not data_list:
            raise Exception("No data in the database")
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_org_filter_list():
    """
    机构列表筛选
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        category = request.args.get("category")  # 机构名称org_name, 昵称传nick
        belong = request.args.get("belong")  # 全部传default, 主账号master, 子账号slave
        content = request.args.get("content")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        sort_way = request.args.get("sort_way")  # -1 倒序 1正序

        # 校验参数
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["org_name", "nick"]:
            error = "category invalid"
        elif belong not in ["default", "master", "slave"]:
            error = "belong invalid"
        elif sort_way not in ["-1", "1"]:
            error = "sort_way invalid"
        # elif not start_time:
        #     error = "start_time is required"
        # elif not end_time:
        #     error = "end_time is required"
        if error:
            return response(msg=error, code=1, status=400)

        startTime, endTime, deltaDay = comm.strDateToTimestamp(start_time, end_time)

        # if deltaDay > constant.queryDayCount:
        #     error = "查询时间范围仅限{}以内".format(constant.queryDayCount)
        if content and len(content) > constant.SEARCH_MAX:
            error = "搜索关键词最多{}个字符".format(constant.SEARCH_MAX)
        if error:
            return response(msg=error, code=1)

        # 查询
        pipeline = [
            {
                "$match": {
                    "type": "org", "state": {"$ne": -1},
                    "belong": {"$in": ["master", "slave"]} if belong == "default" else {"$eq": belong},
                    ("nick" if category == "nick" else "org_name") if content else "null": {
                        "$regex": content} if content else None,
                    "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                        "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None
                }
            },
            {"$sort": SON([("create_time", int(sort_way))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "org_name": 1, "belong": 1, "group": 1, "state": 1, "nick": 1, "account": 1,
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$head_img_url", ""]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                        }
                    },
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        condition = {
            "type": "org", "state": {"$ne": -1},
            "belong": {"$in": ["master", "slave"]} if belong == "default" else {"$eq": belong},
            ("nick" if category == "nick" else "org_name") if content else "null": {
                "$regex": content} if content else None,
            "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None
        }
        count = client["user"].find(condition).count()
        data["count"] = count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_org_name_list():
    """获取机构名称列表"""
    try:
        # 查询
        pipeline = [
            {"$match": {"type": "org", "state": 1, "org_name": {"$ne": None}}},
            {"$group": {"_id": "$org_name"}},
            {"$project": {"_id": 0, "org_name": "$_id"}}
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = []
        for doc in cursor:
            data_list.append(doc["org_name"])
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_create_org_account(domain=constant.DOMAIN, length_max=32, sign_length_max=128, label_length_max=20):
    """
    创建机构账号
    :param domain: 域名
    :param length_max: 昵称长度上限
    :param sign_length_max: 签名长度上限
    :param label_length_max: 标签上限
    """
    try:
        # 获取参数
        nick = request.json.get("nick")
        account = request.json.get("account")
        label = request.json.get("label")  # array
        sex = request.json.get("sex")
        mobile = request.json.get("mobile")
        sign = request.json.get("sign")
        belong = request.json.get("belong")  # 主账号master, 子账号slave
        org_name = request.json.get("org_name")
        group = request.json.get("group")  # comm一般用户，auth认证摄影师
        head_img_url = request.json.get("head_img_url")
        background_url = request.json.get("background_url")
        if not nick:
            return response(msg="请输入昵称", code=1)
        if len(nick) > length_max:
            return response(msg=f"昵称最多{length_max}个字符", code=1)
        if not account:
            return response(msg="请输入账号", code=1)
        if not label:
            return response(msg="请输入标签", code=1)
        if len(label) > label_length_max:
            return response(msg=f"最多允许{label_length_max}个标签", code=1)
        if sex not in ["保密", "男", "女"]:
            return response(msg="请选择性别", code=1)
        if not mobile:
            return response(msg="请输入手机", code=1)
        if len(str(mobile)) != 11:
            return response(msg="请输入正确的手机号", code=1)
        if not re.match(r"1[35678]\d{9}", str(mobile)):
            return response(msg="请输入正确的手机号", code=1)
        if not sign:
            return response(msg="请输入签名", code=1)
        if belong not in ["master", "slave"]:
            return response(msg="请选择账号类型", code=1)
        if belong == 'master' and (not org_name):
            return response(msg="请输入机构名", code=1)
        if group not in ["comm", "auth"]:
            return response(msg="请选择用户组", code=1)

        # 判断手机号是否已经存在
        tmp = client["user"].find_one({"mobile": mobile}, {"_id": 1})
        if tmp:
            return response(msg="手机号已存在，请重新输入", code=1)

        head_img_url = head_img_url.replace(domain, "")
        background_url = background_url.replace(domain, "")
        # 入库
        uid = generate_uid(24)
        # token
        data = {"uid": str(uid)}
        md5_token = hashlib.md5(str(data).encode()).hexdigest()
        data = {"md5_token": md5_token, "timestamp": int(time.time() * 1000)}
        token = base64.b64encode(json.dumps(data).encode()).decode()
        password_b64 = base64.b64encode(str(123456).encode()).decode()

        condition = {
            "uid": uid, "nick": nick, "account": account, "label": label, "sex": sex, "type": "org", "age": 18,
            "sign": sign, "belong": belong, "org_name": org_name, "group": group, 'token': token, "state": 1,
            "head_img_url": head_img_url, "background_url": background_url, "mobile": mobile, "balance": float(0),
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000), "auth": 0, "works_num": 0,
            "login_time": int(time.time() * 1000), "password": password_b64
        }
        client["user"].insert(condition)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 舍弃
def get_user_audit():
    """用户审核列表"""
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        # 查询
        pipeline = [
            {"$match": {"auth": 1, "state": 1, "type": {"$in": ["org", "user"]}}},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "uid": 1, "head_img_url": 1, "nick": 1, "account": 1,
                          "update_time": {"$dateToString": {"format": "%Y-%m-%d %H:%M",
                                                            "date": {"$add": [init_stamp, "$update_time"]}}},
                          "id_card_name": 1, "id_card": 1}}
        ]
        cursor = client["user"].aggregate(pipeline)
        user_list = [doc for doc in cursor]
        condition = {"auth": 1, "state": 1, "type": {"$in": ["org", "user"]}}
        count = client["user"].find(condition).count()
        data["count"] = count
        data["list"] = user_list
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_audit_filter():
    """
    用户审核列表搜索
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        category = request.args.get("category")  # 账号传account, 昵称传nick
        content = request.args.get("content")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        sort_way = request.args.get("sort_way")  # -1 倒序 1正序

        # 校验参数
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num is invalid"
        elif category not in ["account", "nick"]:
            error = "category invalid"
        elif sort_way not in ["-1", "1"]:
            error = "sort_way invalid"
        # elif not start_time:
        #     error = "start_time is required"
        # elif not end_time:
        #     error = "end_time is required"
        if error:
            return response(msg=error, code=1, status=400)

        startTime, endTime, deltaDay = comm.strDateToTimestamp(start_time, end_time)

        # if deltaDay > constant.queryDayCount:
        #     error = "查询时间范围仅限{}以内".format(constant.queryDayCount)
        if content and len(content) > constant.SEARCH_MAX:
            error = "搜索关键词最多{}个字符".format(constant.SEARCH_MAX)
        if error:
            return response(msg=error, code=1)

        # 查询
        pipeline = [
            {
                "$match": {
                    "auth": 1, "state": 1,
                    "type": {"$in": ["org", "user"]},
                    ("nick" if category == "nick" else "account") if content else "null": {
                        "$regex": content} if content else None,
                    "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                        "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None
                }
            },
            {"$sort": SON([("create_time", int(sort_way))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "nick": 1, "account": 1, "id_card_name": 1, "id_card": 1,
                    "update_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$update_time"]}
                        }
                    },
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$head_img_url", ""]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                        }
                    },
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        condition = {
            "auth": 1, "state": 1, "type": {"$in": ["org", "user"]},
            "nick" if category == "nick" else "account" if content else "null": {
                "$regex": content} if content else None,
            "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None
        }
        count = client["user"].find(condition).count()
        data["count"] = count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_audit_state():
    """用户审核"""
    try:
        # 参数
        user_id = request.json.get("user_id")  # array
        auth = request.json.get("auth")  # 通过2, 驳回传0
        note = request.json.get("note")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if auth not in [0, 2]:
            return response(msg="Bad Request:Params 'auth' is error.", code=1, status=400)

        # 驳回原因
        if auth == 0:
            for id in user_id:
                uid = generate_uid(16)
                desc = f"您的摄影师认证申请被驳回, 原因是：{note}"
                client["message"].insert(
                    {
                        "uid": uid, "user_id": id, "push_people": "系统消息", "desc": desc, "type": 1,
                        "state": 1, "create_time": int(time.time() * 1000),
                        "update_time": int(time.time() * 1000)
                    }
                )
                client["user"].update({"uid": id}, {"$set": {"auth": 0}})
        else:
            client["user"].update(
                {"uid": {"$in": user_id}},
                {"$set": {"auth": auth, "group": "auth"}},
                multi=True
            )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_audit_detail(domain=constant.DOMAIN):
    """
    用户审核详情
    :param domain: 域名
    """
    try:
        # 参数
        user_id = request.args.get("user_id")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        # 查询
        pipeline = [
            {"$match": {"uid": user_id}},
            {
                "$project": {
                    "_id": 0, "nick": 1, "account": 1, "mobile": 1, "id_card_name": 1, "home_addr": 1,
                    "id_card_a_url": {"$concat": [domain, "$id_card_a_url"]}, "id_card_addr": 1,
                    "id_card_b_url": {"$concat": [domain, "$id_card_b_url"]}, "id_card": 1,
                    "repre_works": {
                        "$map": {
                            "input": "$repre_works",
                            "as": "item",
                            "in": {"$concat": [domain, "$$item"]}
                        }
                    },
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$head_img_url", ""]},
                            "then": "",
                            "else": {"$concat": [domain, "$head_img_url"]}
                        }
                    }
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        return response(data=data_list[0] if data_list else None)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_group_list():
    """user group category"""
    try:
        data_list = [
            {"name": "一般用户", "group": "comm"},
            {"name": "认证摄影师", "group": "auth"}
        ]
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def postForbiddenSpeech():
    """用户禁言"""
    userId = request.json.get("user_id")
    dayNum = request.json.get("day_num")

    error = None
    if not all([userId, dayNum]):
        error = "miss params"
    elif not isinstance(dayNum, int):
        error = "day_num type is error"
    if error:
        return response(msg=error, code=1, status=400)

    expireTime = int((datetime.datetime.now() + datetime.timedelta(days=dayNum)).timestamp() * 1000)

    # 插入数据库
    try:
        error = users.insertUserForbidden(userId, expireTime)
        if error:
            raise Exception(error)
    except Exception as e:
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)

    return response()


def updateForbiddenSpeech():
    """更新用户禁言状态"""
    userId = request.json.get("user_id")

    error = None
    if not userId:
        error = "miss params"
    if error:
        return response(msg=error, code=1, status=400)

    # 更新
    try:
        error = users.updateUserForbidden(userId)
        if error:
            raise Exception(error)
    except Exception as e:
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)

    return response()
