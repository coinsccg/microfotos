# -*- coding: utf-8 -*-
"""
@Time: 2020/07/19 17:05:31
@File: admin_system_api
@Auth: money
"""
import os
import re
import base64
import time
import hashlib
import json
import datetime
from bson.son import SON
from flask import request
from flask import g
from middleware.auth import response
from utils.util import generate_uid
from initialize import log
from initialize import client
from initialize import init_stamp
from constant import constant
from dao.admin.systems import systems


def get_admin_account_search():
    """
    管理员账号列表搜索
    """
    data = {}
    try:
        # 获取参数
        num = request.args.get("num")
        page = request.args.get("page")
        content = request.args.get("content")
        type = request.args.get("type")  # 账号account 昵称nick 联系电话mobile

        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if type not in ["account", "nick", "mobile"]:
            return response(msg="Bad Request: Params 'type' is erroe.", code=1, status=400)
        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容上限{constant.SEARCH_MAX}个字符", code=1)
        # 查询
        pipeline = [
            {"$match": {"state": {"$ne": -1}, "type": "admin", f"{type}": {"$regex": content}}},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "role",
                    "let": {"role_id": "$role_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$uid", "$$role_id"]}}},
                        {"$group": {"_id": {"uid": "$uid", "nick": "$nick"}}},
                        {"$project": {"_id": 0, "nick": "$_id.nick", "uid": "$_id.uid"}}
                    ],
                    "as": "role_temp_item"
                }
            },
            {
                "$addFields": {
                    "role_list": {
                        "$map": {
                            "input": "$role_temp_item",
                            "as": "item",
                            "in": {"uid": "$$item.uid", "nick": "$$item.nick"}
                        }
                    }
                }
            },
            {"$unset": ["role_temp_item"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "nick": 1, "account": 1, "mobile": 1,
                    "role_list": 1, "role": "$role_name",
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["admin"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        condition = {"state": {"$ne": -1}, "type": "admin", f"{type}": {"$regex": content}}
        count = client["admin"].find(condition).count()
        data["count"] = count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_create_account():
    """创建账号"""
    try:
        # 参数
        account = request.json.get("account")
        nick = request.json.get("nick")
        mobile = request.json.get("mobile")
        role = request.json.get("role")  # array [{"id": , "name": , }]
        if not account:
            return response(msg="Bad Request: Miss params: 'account'.", code=1, status=400)
        if not nick:
            return response(msg="Bad Request: Miss params: 'nick'.", code=1, status=400)
        if not mobile:
            return response(msg="Bad Request: Miss params: 'mobile'.", code=1, status=400)
        if not role:
            return response(msg="请选择角色", code=1)
        if len(str(mobile)) != 11:
            return response(msg="请输入正确的手机号", code=1)
        if not re.match(r"1[35678]\d{9}", str(mobile)):
            return response(msg="请输入正确的手机号", code=1)
        doc = client["admin"].find_one({"account": account, "state": 1, "type": "admin"})
        if doc:
            return response(msg="账号已经存在", code=1)

        uid = generate_uid(24)
        password = "123456"
        password_b64 = base64.b64encode(str(password).encode()).decode()

        # token
        data = {"uid": str(uid)}
        md5_token = hashlib.md5(str(data).encode()).hexdigest()
        data = {"md5_token": md5_token, "timestamp": int(time.time() * 1000)}
        token = base64.b64encode(json.dumps(data).encode()).decode()

        condition = {
            "uid": uid, "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000),
            "account": account, "nick": nick, "mobile": mobile, "password": password_b64, "token": token,
            "role_id": [obj["id"] for obj in role], "role_name": "、".join([obj["nick"] for obj in role]),
            "login_time": int(time.time() * 1000), "sex": "保密", "age": 18, "type": "admin"
        }
        client["admin"].insert(condition)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_admin_password_reset():
    """重置密码"""
    try:
        # 参数
        user_id = request.json.get("user_id")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        password = "123456"
        password_b64 = base64.b64encode(str(password).encode()).decode()
        client["admin"].update({"uid": user_id}, {"$set": {"password": password_b64}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_admin_account_state():
    """管理员列表页删除操作"""
    try:
        # 参数
        user_id = request.json.get("user_id")
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        doc = client["admin"].update({"uid": user_id}, {"$set": {"state": -1}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_admin_permission_list():
    """权限明细列表"""
    data = {}
    try:
        # 差选
        pipeline = [
            {"$match": {"state": 1, "uid": {"$ne": "002"}, "module_id": {"$ne": "008"}}},
            {"$unset": ["create_time", "update_time", "state", "_id"]},
            {"$sort": SON([("uid", 1)])},
            {"$group": {"_id": {"menu": "$menu", "module_id": "$module_id"}, "permission_item": {"$push": "$$ROOT"}}},
            {"$unset": ["permission_item.module_id", "permission_item.menu"]},
            {"$project": {"_id": 0, "menu": "$_id.menu", "module_id": "$_id.module_id", "permission_item": 1}},
            {
                "$lookup": {
                    "from": "module",
                    "let": {"module_id": "$module_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$module_id"]}}}],
                    "as": "module_item"
                }
            },
            {"$addFields": {"module_info": {"$arrayElemAt": ["$module_item", 0]}}},
            {"$addFields": {"module_name": "$module_info.name"}},
            {"$unset": ["module_info", "module_item"]},
            {"$group": {"_id": {"module_name": "$module_name", "module_id": "$module_id"},
                        "item": {"$push": "$$ROOT"}}},
            {"$unset": ["item.module_name", "item.module_id"]},
            {"$project": {"_id": 0, "module_id": "$_id.module_id", "module_name": "$_id.module_name", "item": 1}},
            {"$sort": SON([("module_id", 1)])}
        ]
        cursor = client["permission"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_admin_account_alter(nick_length_max=32):
    """
    账号修改接口
    :param nick_length_max: 昵称最大上限
    """
    try:
        # 参数
        user_id = request.json.get("user_id")
        account = request.json.get("account")
        nick = request.json.get("nick")
        mobile = request.json.get("mobile")
        role_id = request.json.get("role_id")  # array [{"id": , "nick": , }]
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if not account:
            return response(msg="Bad Request: Miss params: 'account'.", code=1, status=400)
        if not nick:
            return response(msg="Bad Request: Miss params: 'nick'.", code=1, status=400)
        if len(nick) > nick_length_max:
            return response(msg=f"昵称最长{nick_length_max}个字符", code=1)
        if not role_id:
            return response(msg="Bad Request: Miss params: 'role_id'.", code=1, status=400)
        if not mobile:
            return response(msg="Bad Request: Miss params: 'mobile'.", code=1, status=400)
        if len(str(mobile)) != 11:
            return response(msg="请输入正确的手机号", code=1)
        if not re.match(r"1[35678]\d{9}", str(mobile)):
            return response(msg="请输入正确的手机号", code=1)
        role_name = "、".join([doc["nick"] for doc in role_id])
        client["admin"].update(
            {"uid": user_id},
            {"$set": {
                "account": account, "mobile": mobile, "nick": nick,
                "role_id": [doc["id"] for doc in role_id],
                "role_name": role_name
            }}
        )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_add_permissions_role(nick_length_max=32, desc_length_max=128):
    """
    创建角色
    :param nick_length_max: 昵称上限
    :param desc_length_max: 描述上限
    """
    try:
        # 参数
        nick = request.json.get("nick")
        desc = request.json.get("desc")
        permission_list = request.json.get(
            'permission_list')  # [{"module_id": "001", "permission_id": "001"}, ...] or  [{"module_id": "001", "permission_id": ["001", "002", ...]},...]
        if not nick:
            return response(msg="Bad Request: Miss params: 'nick'.", code=1, status=400)
        if len(nick) > nick_length_max:
            return response(msg=f"昵称上限{nick_length_max}个字符", code=1, status=400)
        if not desc:
            return response(msg="Bad Request: Miss params: 'desc'.", code=1, status=400)
        if len(desc) > desc_length_max:
            return response(msg=f"描述上限{desc_length_max}个字符", code=1, status=400)
        if not permission_list:
            return response(msg="请选择权限", code=1)

        uid = generate_uid(24)
        n = 0
        temp_dict = {}
        template = {
            "uid": uid, "nick": nick, "desc": desc, "module_id": "",
            "permission_id": "", "state": 1,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }

        for obj in permission_list:

            template["permission_id"] = obj["permission_id"]
            template["module_id"] = obj["module_id"]

            if obj["module_id"] == "001":
                n += 1

            doc = client["permission"].find_one({"uid": obj["permission_id"], "module_id": obj["module_id"]})
            if doc["menu"] not in temp_dict:
                temp_dict[doc["menu"]] = 0
            if doc["name"] == "查看":
                if doc["menu"] not in temp_dict:
                    temp_dict[doc["menu"]] = 1
                temp_dict[doc["menu"]] += 1
            client["role"].insert(template)
            if "_id" in template:
                template.pop("_id")

        if n == 0:
            template["permission_id"] = "002"
            template["module_id"] = "001"
            if "_id" in template:
                template.pop("_id")
            client["role"].insert(template)

        temp_list = []
        for i in temp_dict.keys():
            if temp_dict[i] == 0:
                doc = client["permission"].find_one({"menu": i, "name": "查看"})
                temp1 = {
                    "uid": uid, "nick": nick, "desc": desc, "module_id": doc["module_id"], "permission_id": doc["uid"],
                    "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
                temp_list.append(temp1)
        if temp_list:
            client["role"].insert(temp_list)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_role_list():
    """获取角色列表"""
    try:
        # 查询
        pipeline = [
            {"$match": {"state": 1, "uid": {"$ne": "super001"}}},
            {
                "$group": {
                    "_id": {
                        "uid": "$uid", "nick": "$nick", "desc": "$desc", "module_id": "$module_id",
                        "permission_id": "$permission_id"
                    }, "create_time": {"$first": "$create_time"}
                }
            },
            {
                "$project": {
                    "_id": 0, "uid": "$_id.uid", "nick": "$_id.nick", "desc": "$_id.desc",
                    "module_id": "$_id.module_id", "permission_id": "$_id.permission_id", "create_time": "$create_time"
                }
            },
            {
                "$group": {
                    "_id": {"uid": "$uid", "nick": "$nick", "desc": "$desc"},
                    "permission_list": {"$push": "$$ROOT"}, "create_time": {"$first": "$create_time"}
                }
            },
            {"$unset": ["permission_list._id", "permission_list.uid", "permission_list.nick", "permission_list.desc"]},
            {"$sort": SON([("create_time", -1)])},
            {"$project": {"_id": 0, "uid": "$_id.uid", "nick": "$_id.nick", "desc": "$_id.desc", "permission_list": 1}},
        ]
        cursor = client["role"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        return response(data=data_list if data_list else [])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_role_state():
    """角色删除接口"""
    try:
        # 参数
        role_id = request.json.get("role_id")
        if not role_id:
            return response(msg="Bad Request: Miss params: 'role_id'.", code=1, status=400)
        doc = client["role"].update({"uid": role_id}, {"$set": {"state": -1}}, multi=True)
        if doc["n"] == 0:
            return response(msg="Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_admin_operation_log(delta_time=30, length_max=32):
    """
    日志列表接口
    :param delta_time: 允许查询的最大区间30天
    :param length_max: 搜索上限
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        content = request.args.get("content")
        type = request.args.get("type")  # account账号 nick昵称 mobile电话
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)
        # 校验
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if type not in ["account", "nick"]:
            return response(msg="Bad Request: Params 'type' is error.", code=1, status=400)
        temp_list = (int(end_time) - int(start_time)) // (24 * 3600 * 1000)
        if temp_list > delta_time:
            return response(msg=f"最大只能查询{delta_time}天之内的记录", code=1)
        pipeline = [
            {
                "$match": {
                    "$and": [
                        {"create_time": {"$gte": int(start_time)}},
                        {"create_time": {"$lte": int(end_time)}}
                    ],
                    type if content else "null": {"$regex": content} if content else None
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "nick": 1, "account": 1, "mobile": 1, "ip": 1, "content": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["log"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        data["list"] = data_list
        # 总数
        condition = {
            "$and": [
                {"create_time": {"$gte": int(start_time)}},
                {"create_time": {"$lte": int(end_time)}}
            ],
            type if content else "null": {"$regex": content} if content else None
        }
        count = client["log"].find(condition).count()
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_add_permissions_role_editor(nick_length_max=32, desc_length_max=128):
    """
    编辑角色
    :param nick_length_max: 昵称上限
    :param desc_length_max: 描述上限
    """
    try:
        # 参数
        uid = request.json.get("uid")
        nick = request.json.get("nick")
        desc = request.json.get("desc")
        permission_list = request.json.get(
            'permission_list')  # [{"module_id": "001", "permission_id": "001"}, ...] or  [{"module_id": "001", "permission_id": ["001", "002", ...]},...]
        if not uid:
            return response(msg="Bad Request: Miss params: 'uid'.", code=1, status=400)
        if not nick:
            return response(msg="Bad Request: Miss params: 'nick'.", code=1, status=400)
        if len(nick) > constant.NICK_MAX:
            return response(msg=f"昵称上限{constant.NICK_MAX}个字符", code=1, status=400)
        if not desc:
            return response(msg="Bad Request: Miss params: 'desc'.", code=1, status=400)
        if len(desc) > constant.DESC_MAX:
            return response(msg=f"描述上限{constant.DESC_MAX}个字符", code=1, status=400)
        client["role"].delete_many({"uid": uid})

        n = 0
        temp_dict = {}
        template = {
            "uid": uid, "nick": nick, "desc": desc, "module_id": "", "permission_id": "", "state": 1,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }

        for obj in permission_list:
            template["permission_id"] = obj["permission_id"]
            template["module_id"] = obj["module_id"]

            if obj["module_id"] == "001":
                n += 1

            doc = client["permission"].find_one({"uid": obj["permission_id"], "module_id": obj["module_id"]})
            if doc["menu"] not in temp_dict:
                temp_dict[doc["menu"]] = 0
            if doc["name"] == "查看":
                if doc["menu"] not in temp_dict:
                    temp_dict[doc["menu"]] = 1
                temp_dict[doc["menu"]] += 1
            client["role"].insert(template)
            if "_id" in template:
                template.pop("_id")

        if n == 0:
            template["permission_id"] = "002"
            template["module_id"] = "001"
            if "_id" in template:
                template.pop("_id")
            client["role"].insert(template)

        temp_list = []
        for i in temp_dict.keys():
            if temp_dict[i] == 0:
                doc = client["permission"].find_one({"menu": i, "name": "查看"})
                temp1 = {
                    "uid": uid, "nick": nick, "desc": desc, "module_id": doc["module_id"], "permission_id": doc["uid"],
                    "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }

                temp_list.append(temp1)
        if temp_list:
            client["role"].insert(temp_list)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_system_backup_list():
    """备份列表"""
    data = {}
    try:
        page = request.args.get("page")
        num = request.args.get("num")
        if not num:
            return response(msg="Bad Request: Miss param 'num'.", code=1, status=400)
        if int(num) < 1 or int(page) < 1:
            return response(msg="Bad Request: Param 'page' or 'num' is error.", code=1, status=400)
        pipeline = [
            {"$match": {"state": 1}},
            {"$sort": SON([("create_time", -1)])},
            {
                "$group": {
                    "_id": {
                        "uid": "$uid", "name": "$name", "instruction": "$instruction"
                    },
                    "create_time": {"$first": "$create_time"}
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": "$_id.uid", "name": "$_id.name",
                    "instruction": "$_id.instruction",
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["backup"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        pipeline = [
            {"$match": {"state": 1}},
            {
                "$group": {
                    "_id": {
                        "uid": "$uid", "name": "$name", "instruction": "$instruction"
                    }
                }
            },
            {"$count": "count"}
        ]
        cursor = client["backup"].aggregate(pipeline)
        temp_list = [doc for doc in cursor]
        count = temp_list[0]["count"] if temp_list else 0
        data["list"] = data_list
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def delete_backup_state():
    """删除备份记录"""
    try:
        # 参数
        uid = request.json.get("uid")
        if not uid:
            return response(msg="Bad Request: Miss params: 'uid'.", code=1, status=400)
        doc = client["backup"].update({"uid": uid}, {"$set": {"state": -1}}, multi=True)
        if doc["n"] == 0:
            return response(msg="Bad Request: Params 'uid' is error.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_system_backup():
    """系统备份"""
    try:
        # 参数
        name = request.json.get("name")
        instruction = request.json.get("instruction")
        if not name:
            return response(msg="请输入备份名称", code=1)
        if not instruction:
            return response(msg="请输入备份说明", code=1)
        """
        备份内容：角色权限、平台定价、可选栏目、热搜词、文档管理、评论敏感词
        """
        BASE_DIR = os.getcwd()
        path_list = []
        timestamp = int(time.time() * 1000)

        # 角色权限备份
        cursor_module = client["module"].find({}, {"_id": 0})
        module_list = list(cursor_module)
        cursor_permission = client["permission"].find({}, {"_id": 0})
        permission_list = list(cursor_permission)
        cursor_role = client["role"].find({}, {"_id": 0})
        role_list = list(cursor_role)
        module_path = f"/statics/files/backup/module/"
        print(BASE_DIR)
        if not os.path.exists(BASE_DIR + module_path):
            os.makedirs(BASE_DIR + module_path)
        permission_path = f"/statics/files/backup/permission/"
        if not os.path.exists(BASE_DIR + permission_path):
            os.makedirs(BASE_DIR + permission_path)
        role_path = f"/statics/files/backup/role/"
        if not os.path.exists(BASE_DIR + role_path):
            os.makedirs(BASE_DIR + role_path)
        path_list += [
            module_path + f"{timestamp}.json",
            permission_path + f"{timestamp}.json",
            role_path + f"{timestamp}.json"
        ]
        with open(BASE_DIR + module_path + f"{timestamp}.json", "w") as f:
            f.write(json.dumps(module_list))
        with open(BASE_DIR + permission_path + f"{timestamp}.json", "w") as f:
            f.write(json.dumps(permission_list))
        with open(BASE_DIR + role_path + f"{timestamp}.json", "w") as f:
            f.write(json.dumps(role_list))

        # 平台定价
        cursor_price = client["price"].find({"uid": "001"}, {"_id": 0})
        price_list = list(cursor_price)
        price_path = f"/statics/files/backup/price/"
        if not os.path.exists(BASE_DIR + price_path):
            os.makedirs(BASE_DIR + price_path)
        path_list.append(price_path + f"{timestamp}.json")
        with open(BASE_DIR + price_path + f"{timestamp}.json", "w") as f:
            f.write(json.dumps(price_list))

        # 敏感词
        cursor_bad = client["bad"].find({}, {"_id": 0})
        bad_list = list(cursor_bad)
        bad_path = f"/statics/files/backup/bad/"
        if not os.path.exists(BASE_DIR + bad_path):
            os.makedirs(BASE_DIR + bad_path)
        path_list.append(bad_path + f"{timestamp}.json")
        with open(BASE_DIR + bad_path + f"{timestamp}.json", "w") as f:
            f.write(json.dumps(bad_list))

        # 文档管理
        cursor_document = client["document"].find({}, {"_id": 0})
        document_list = list(cursor_document)
        document_path = f"/statics/files/backup/document/"
        if not os.path.exists(BASE_DIR + document_path):
            os.makedirs(BASE_DIR + document_path)
        path_list.append(document_path + f"{timestamp}.json")
        with open(BASE_DIR + document_path + f"{timestamp}.json", "w") as f:
            f.write(json.dumps(document_list))

        # 入库
        uid = generate_uid(24)
        condition = []
        for i in path_list:
            obj = {
                "uid": uid, "name": name, "instruction": instruction, "file_path": i,
                "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
            condition.append(obj)
        client["backup"].insert_many(condition)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_system_backup_reduction():
    """备份恢复"""
    try:
        uid = request.json.get("uid")
        if not uid:
            return response(msg="Bad Request: Miss params: 'uid'.", code=1, status=400)
        cursor = client["backup"].find({"uid": uid})
        data_list = [doc["file_path"] for doc in cursor]
        if not data_list:
            return response(msg="Bad Request: Params 'uid' is error.", code=1, status=400)
        BASE_DIR = os.getcwd()
        for i in data_list:
            with open(BASE_DIR + i, "rb") as f:
                temp = i.split("/")[4]
                data = json.loads(f.read().decode("utf-8"))
            if temp == "price":
                for p in data:
                    client["price"].update(
                        {"uid": "001", "format": p["format"]},
                        {
                            "$set": {
                                "price": p["price"], "create_time": int(time.time() * 1000),
                                "update_time": int(time.time() * 1000)
                            }
                        }
                    )
            else:
                client[f"{temp}"].drop()
                client[f"{temp}"].insert_many(data)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_upload_apk():
    """
    上传apk安装包
    """
    data = {}
    try:
        file = request.files.get("file")
        if not file:
            return response(msg="Bad Request: Miss param 'file'.", status=1, code=400)

        path = os.getcwd() + "/statics/files/install"
        uid = hashlib.md5(base64.b64encode(os.urandom(16))).hexdigest()
        if not os.path.exists(path):
            os.makedirs(path)
        dir_path = f"/microfots_{uid}.apk"
        with open(path + dir_path, "wb") as f:
            f.write(file.read())

        package_size = os.path.getsize(path + dir_path)
        data["path"] = constant.DOMAIN + "/install" + dir_path
        data["size"] = round(package_size / (1024 * 1024), 2)
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def get_version_list():
    """版本列表"""
    data = {}
    try:
        page = request.args.get("page")
        num = request.args.get("num")

        # 参数校验
        error = None
        if not page:
            error = "page is required"
        elif not num:
            error = "num is required"
        elif not (page.isdigit() and num.isdigit()):
            error = "page or num invalid"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        if error:
            return response(msg=error, code=1, status=400)

        # 查询数据
        dataList, count, error = systems.queryVersionList(page, num)
        if error:
            raise Exception(error)

        data["list"] = dataList
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def put_version_state():
    """删除版本"""
    try:

        uid = request.json.get("uid")
        if not uid:
            return response(msg="uid is required", status=1, code=400)

        # 删除
        error = systems.deleteVersion(uid)
        if error:
            raise Exception(error)

        return response()
    except Exception as e:
        return response(msg="Internal Serve Error: %s." % str(e), code=1, status=500)


def post_version_add():
    """
    添加版本号
    """
    try:
        # param verify
        version_name = request.json.get("version_name")
        version_str = request.json.get("version_str")
        version_num = request.json.get("version_num")
        option = request.json.get("option")  # 1提示更新， 2强制更新
        tip_way = request.json.get("tip_way")  # 1弹窗提示， 2站内提示, 3权选
        desc = request.json.get("desc")
        link = request.json.get("link")
        size = request.json.get("size")

        # 参数校验
        error = None
        if not version_name:
            error = "请输入版本名称"
        elif not version_str:
            error = "请输入版本号"
        elif not version_num:
            error = "请输入版本序号"
        elif type(version_num) != int:
            error = "请输入正确的版本序号"
        if error:
            return response(msg=error, code=1)

        if option not in [1, 2]:
            error = "option invalid"
        elif tip_way not in [1, 2, 3]:
            error = "tip_way invalid"
        elif not link:
            error = "link is required"
        elif type(link) != str:
            error = "link type is error"
        elif not size:
            error = "size required"
        elif type(size) == str:
            error = "size type is error"
        if error:
            return response(msg=error, code=1, status=400)

        link = link.replace(constant.DOMAIN, "")
        uid = hashlib.md5(base64.b64encode(os.urandom(16))).hexdigest()

        # 判断版本号是否存在
        result1, result2, error = systems.queryVersionNo(version_str, version_num)
        if result1:
            return response(msg="版本号重复", code=1)
        if result2:
            return response(msg="版本序号重复", code=1)
        if error:
            raise Exception(error)

        # 添加版本
        error = systems.insertVersion(uid, version_name, version_str, option, link, size, desc, version_num, tip_way)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Serve: %s." % str(e), code=1, status=500)


def put_version_info():
    """
    编辑版本
    """
    try:
        # param verify
        uid = request.json.get("uid")
        version_name = request.json.get("version_name")
        version_str = request.json.get("version_str")
        version_num = request.json.get("version_num")
        option = request.json.get("option")  # 1提示更新， 2强制更新
        tip_way = request.json.get("tip_way")  # 1弹窗提示， 2站内提示
        desc = request.json.get("desc")
        link = request.json.get("link")
        size = request.json.get("size")

        error = None
        if not version_name:
            error = "请输入版本名称"
        elif not version_str:
            error = "请输入版本号"
        elif not version_num:
            error = "请输入版本序号"
        elif type(version_num) != int:
            error = "请输入正确的版本序号"
        if error:
            return response(msg=error, code=1)

        if option not in [1, 2]:
            error = "option invalid"
        elif tip_way not in [1, 2, 3]:
            error = "tip_way invalid"
        elif not link:
            error = "link is required"
        elif type(link) != str:
            error = "link type is error"
        elif not size:
            error = "size required"
        elif type(size) == str:
            error = "size type is error"
        elif not uid:
            error = "uid is required"
        if error:
            return response(msg=error, code=1, status=400)

        link = link.replace(constant.DOMAIN, "")

        # 判断版本号是否重复
        result1, result2, error = systems.queryAllVersionNo(uid, version_str, version_num)
        if result1:
            return response(msg="版本号重复", code=1)
        if result2:
            return response(msg="版本序号重复", code=1)
        if error:
            raise Exception(error)

        # 更新版本
        error = systems.updateVersion(uid, version_name, version_str, version_num, option, desc, link, size, tip_way)
        if error:
            raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server: %s." % str(e), code=1, status=500)


def get_version_latest_list():
    """获取序号列表"""
    try:
        dataList, error = systems.queryVersionNoList()
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)


def post_latest_version():
    """设置最新版本号"""
    try:
        version_str = request.json.get("version_str")
        if not version_str:
            return response(msg="version_str is required", status=1, code=400)
        error = systems.postLatestVersionNo(version_str)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), code=1, status=500)
