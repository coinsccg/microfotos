# -*- coding: utf-8 -*-
"""
@Time: 2020/07/19 15:20:23
@File: admin_login_api
@Auth: money
"""
import time
import hashlib
from flask import request
from middleware.auth import response
from initialize import log
from initialize import client
from middleware.auth import generateJWT


def post_admin_login():
    """管理员登录接口"""
    data = {}
    try:
        account = request.json.get("account")
        password = request.json.get("password")

        # 校验
        error = None
        if not account:
            error = "请输入账号"
        if not password:
            error = "请输入密码"
        if error is not None:
            return response(msg=error, code=1)

        condition = {
            "_id": 0, "uid": 1, "role_id": 1, "token": 1,
            "sign": 1, "mobile": 1, "login_time": 1, "nick": 1, "sex": 1
        }
        passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()
        adminOne = client["admin"].find_one({"account": account, "password": passwordMd5, "state": 1}, condition)
        if not adminOne:
            error = "账号或密码错误"
        if adminOne.get("state") == 0:
            error = "您的账号已被冻结，请联系超级管理员"
        if error is not None:
            return response(msg=error, code=1)

        # 角色权限
        pipeline = [
            {"$match": {"uid": {"$in": adminOne.get("role_id")}, "state": 1}},
            {
                "$lookup": {
                    "from": "module",
                    "let": {"module_id": "$module_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$module_id"]}}}],
                    "as": "module_item"
                }
            },
            {
                "$lookup": {
                    "from": "permission",
                    "let": {"permission_id": "$permission_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$permission_id"]}}}],
                    "as": "permission_item"
                }
            },
            {
                "$addFields": {
                    "module_info": {"$arrayElemAt": ["$module_item", 0]},
                    "permission_info": {"$arrayElemAt": ["$permission_item", 0]}
                }
            },
            {
                "$addFields": {
                    "module_name": "$module_info.name",
                    "permission_name": "$permission_info.name",
                    "menu": "$permission_info.menu"
                }
            },
            {
                "$unset": [
                    "create_time", "update_time", "state", "_id", "module_item", "nick", "uid",
                    "permission_item", "permission_info", "module_info", "desc", "module_name"
                ]
            },
            {
                "$group": {
                    "_id": {"menu": "$menu", "module_id": "$module_id"},
                    "permission_item": {"$push": "$$ROOT"}
                }
            },
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
            {
                "$group": {
                    "_id": {"module_name": "$module_name", "module_id": "$module_id"},
                    "item": {"$push": "$$ROOT"}
                }
            },
            {"$unset": ["item.module_name", "item.module_id"]},
            {"$project": {"_id": 0, "module_id": "$_id.module_id", "module_name": "$_id.module_name", "item": 1}}
        ]
        cursor = client["role"].aggregate(pipeline)
        role_info = [doc for doc in cursor]
        data["role_info"] = role_info
        data["user_info"] = adminOne

        # 生成jwt
        uid = adminOne["uid"]
        token = generateJWT(uid)

        # 最新登录时间
        client["admin"].update_one({"uid": uid}, {"$set": {"login_time": int(time.time() * 1000)}})

        resp = response(data=data)
        resp.headers["token"] = token

        return resp
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def put_admin_password(pwd_length_min=6, pwd_length_max=50):
    """
    修改管理员密码
    :param pwd_length_min: 密码最低位数
    :param pwd_length_max: 密码最高位数
    """
    try:
        # 参数
        user_id = request.json.get("user_id")
        old_password = request.json.get("old_password")
        new_password = request.json.get("new_password")

        # 校验
        passwordLen = len(new_password)
        error = None
        if not old_password:
            error = "请输入旧密码"
        if not new_password:
            error = "请输入新密码"
        if not pwd_length_max >= passwordLen >= pwd_length_min:
            error = "密码长度6-50位"
        if error is not None:
            return response(msg=error, code=1)

        passwordMd5Old = hashlib.md5(str(old_password).encode("utf-8")).hexdigest()
        doc = client["admin"].find_one({"uid": user_id, "password": passwordMd5Old})

        if not doc:
            error = "旧密码错误"
        if old_password == new_password:
            error = "新密码不能与旧密码相同"
        if error is not None:
            return response(msg=error, code=1)

        passwordMd5New = hashlib.md5(str(new_password).encode("utf-8")).hexdigest()
        client["admin"].update({"uid": user_id}, {"$set": {"password": passwordMd5New}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
