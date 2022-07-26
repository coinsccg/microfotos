# -*- coding: utf-8 -*-
"""
@Time: 2020-11-13 16:12:11
@File: auth
@Auth: money
"""
import time
import datetime
import functools
import jwt

from flask import jsonify
from flask import request
from flask import g
from flask import make_response

from initialize import client
from initialize import log
from constant.constant import SECRET
from dao.app.user.user import getUser


def auth_user_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_data = {
            "user_id": None,
            "user_info": None
        }
        try:
            token = request.headers.get("token")
            if token:
                uid, result = verifyJWT(token)
                if not result:
                    return response(msg="登录失效", code=1, status=401)
                userDoc, error = getUser(uid)
                if error is not None:
                    return response(msg="登录失效", code=1, status=401)

                uid = userDoc.get("uid")
                user_data = {"user_id": uid, "user_info": userDoc}

                # 更新禁言状态
                tmp = client["forbidden"].find_one({"user_id": uid, "state": 1})
                if tmp is not None:
                    if tmp.get("expire_time") <= int(time.time() * 1000):
                        client["forbidden"].update_one({"user_id": uid}, {"$set": {"state": -1}})
                        client["user"].update_one({"uid": uid}, {"$set": {"state": 1}})
        except Exception as e:
            log.error(e)
        finally:
            g.user_data = user_data
        return f(*args, **kwargs)

    return wrapper


def auth_admin_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # 验证token
            token = request.headers.get("token")
            if not token:
                return response(msg="Bad Request: Miss params 'token'.", code=1, status=400)
            doc = client["admin"].find_one(
                {"token": token},
                {"_id": 0, "uid": 1, "nick": 1, "sex": 1, "mobile": 1, "role_id": 1, "account": 1}
            )
            if not doc:
                return response(msg="Token fails, please login again.", code=1, status=401)
            uid = doc.get("uid")
            user_data = {
                "user_id": uid,
                "user_info": doc
            }
            g.user_data = user_data
        except Exception as e:
            log.error(e)
            return
        return f(*args, **kwargs)

    return wrapper


def auth_amdin_role(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # 验证token
            module_id = request.headers.get("module_id")
            permission_id = request.headers.get("permission_id")
            if not module_id:
                return response(msg="Bad Request: Miss params 'module_id'.", code=1, status=400)
            if not permission_id:
                return response(msg="Bad Request: Miss params 'permission_id'.", code=1, status=400)
            doc = client["role"].find_one({"module_id": module_id, "permission_id": permission_id})
            if not doc:
                return response(msg="您没有操作权限，请联系超级管理员", code=1)
        except Exception as e:
            log.error(e)
            return
        return f(*args, **kwargs)

    return wrapper


def response(data=None, msg="Request successful.", code=0, status=200):
    """
    统一响应格式
    :param data: 响应数据
    :param msg: 响应信息
    :param code: 错误码 1错误 0正常 默认0
    :param status: http状态码 默认200
    :return
    """
    return make_response(jsonify({"data": data, "msg": msg, "code": code}), status)


def generateJWT(uid: str):
    payload = dict()
    payload['exp'] = int((datetime.datetime.now() + datetime.timedelta(hours=365 * 24)).timestamp() * 1000)
    payload['uid'] = uid
    token = jwt.encode(payload=payload, key=SECRET)
    return token


def verifyJWT(token: str):
    try:
        result = jwt.decode(token, SECRET, algorithms=['HS256'])
        uid = result.get("uid")
        if result.get("exp") <= int(time.time() * 1000):
            return uid, False
        return uid, True
    except Exception as e:
        return "", False
