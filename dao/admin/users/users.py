# -*- coding: utf-8 -*-
"""
@Time: 2021/1/25 13:24
@Auth: money
@File: users.py
"""
import time

from initialize import client


def insertUserForbidden(userId, expireTime):
    error = None
    try:
        doc = {
            "user_id": userId, "expire_time": expireTime, "state": 1, "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        client["forbidden"].insert(doc)

        updateUserState(userId, 2)
    except Exception as e:
        error = e
    finally:
        return error


def updateUserForbidden(userId):
    error = None
    try:
        client["forbidden"].update_one({"user_id": userId, "state": 1}, {"$set": {"state": -1}})
        updateUserState(userId, 1)
    except Exception as e:
        error = e
    finally:
        return error


def getUserForbidden(userId):
    error = None
    data = {}
    try:
        data = client["forbidden"].find_one({"user_id": userId, "state": 1})
    except Exception as e:
        error = e
    finally:
        return data, error


def updateUserState(userId, state):
    error = None
    try:
        client["user"].update_one({"uid": userId}, {"$set": {"state": state}})
    except Exception as e:
        error = e
    finally:
        return error
