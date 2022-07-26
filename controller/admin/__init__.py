# -*- coding: utf-8 -*-
"""
@Time: 2020/11/25 14:57
@Auth: money
@File: __init__
"""
import time
from flask import request
from flask import g

from initialize import client
from utils.util import generate_uid


def log_records(permission_id):
    if permission_id:
        doc = client["permission"].find_one({"uid": permission_id}, {"_id": 0, "name": 1, "menu": 1})
        uid = generate_uid(24)
        temp = {
            "uid": uid,
            "user_id": g.user_data["user_id"],
            "nick": g.user_data["user_info"]["nick"],
            "account": g.user_data["user_info"]["account"],
            "mobile": g.user_data["user_info"]["mobile"],
            "ip": request.remote_addr,
            "content": doc["menu"] + "/" + doc["name"],
            "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        client["log"].insert(temp)
