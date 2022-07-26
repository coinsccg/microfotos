# -*- coding: utf-8 -*-
"""
@Time: 2021/1/15 9:20
@Auth: money
@File: systems.py
"""
import time

from bson.son import SON

from initialize import client
from initialize import init_stamp
from constant import constant
from utils.util import generate_uid


def queryVersionList(page, num):
    dataList = []
    count = 0
    error = None
    try:
        pipeline = [
            {"$match": {"state": 1}},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "version_name": 1, "version_str": 1, "option": 1, "desc": 1, "tip_way": 1,
                    "link": {"$concat": [constant.DOMAIN, "$link"]}, "version_num": 1, "create_time": 1, "size": 1
                }
            }
        ]

        dataList = list(client["version"].aggregate(pipeline))
        count = client["version"].find({"state": 1}).count()
    except Exception as e:
        error = e
    finally:
        return dataList, count, error


def deleteVersion(uid):
    error = None
    try:
        doc = client["version"].find_one({"uid": uid}, {"is_latest": 1})
        client["version"].update_one({"uid": uid}, {"$set": {"state": -1}})
        if doc:
            if doc.get("is_latest"):
                tmp = client["version"].find_one({"state": 1}, {"uid": 1, "version_str": 1, "desc": 1, "tip_way": 1},
                                                 sort=[("version_num", -1)])
                if tmp:
                    client["version"].update_one({"uid": tmp.get("uid")}, {"$set": {"is_latest": True}})
                    if tmp.get("tip_way") != 1:
                        sendAllUserUpateVersion(tmp.get("version_str"), tmp.get("desc"))
    except Exception as e:
        error = e
    finally:
        return error


def queryVersionNo(version_str, version_num):
    result1 = False
    result2 = False
    error = None
    try:
        doc = client["version"].find_one({"version_str": version_str, "state": 1})
        if doc:
            result1 = True
        doc = client["version"].find_one({"version_num": version_num, "state": 1})
        if doc:
            result2 = True
    except Exception as e:
        error = e
    finally:
        return result1, result2, error


def insertVersion(uid, name, version_str, option, link, size, desc, version_num, tip_way):
    error = None
    try:

        updateAllVersionLatestISFalse()
        client["version"].insert(
            {
                "uid": uid, "version_name": name, "version_str": str(version_str), "option": option, "tip_way": tip_way,
                "link": link, "size": float(size), "create_time": int(time.time() * 1000), "desc": str(desc),
                "update_time": int(time.time() * 1000), "version_num": version_num, "state": 1, "is_latest": True
            }
        )
        if tip_way != 1:
            sendAllUserUpateVersion(version_str, desc)
    except Exception as e:
        error = e
    finally:
        return error


def updateVersion(uid, name, version_str, version_num, option, desc, link, size, tip_way):
    error = None
    try:
        updateAllVersionLatestISFalse()
        client["version"].update_one(
            {"uid": uid},
            {
                "$set": {
                    "version_name": name, "version_str": version_str, "version_num": version_num, "option": option,
                    "desc": desc, "link": link, "size": float(size), "tip_way": tip_way, "is_latest": True
                }
            }
        )
        if tip_way != 1:
            sendAllUserUpateVersion(version_str, desc)
    except Exception as e:
        error = e
    finally:
        return error


def queryAllVersionNo(uid, version_str, version_num):
    result1 = False
    result2 = False
    error = None
    try:
        tmp = client["version"].find_one({"uid": uid, "state": 1}, {"version_str": 1, "version_num": 1})
        if tmp:
            if version_str != tmp.get("version_str"):
                tmp1 = client["version"].find_one({"version_str": version_str, "state": 1}, {"_id": 1})
                if tmp1:
                    result1 = True
            if version_num != tmp.get("version_num"):
                tmp2 = client["version"].find_one({"version_num": version_num, "state": 1}, {"_id": 1})
                if tmp2:
                    result2 = True
        else:
            raise Exception("uid is not exists")
    except Exception as e:
        error = e
    finally:
        return result1, result2, error


def queryVersionNoList():
    dataList = []
    error = None
    try:
        cursor = client["version"].find({"state": 1}, {"_id": 0, "version_str": 1, "is_latest": 1})
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def postLatestVersionNo(version_str):
    error = None
    try:
        updateAllVersionLatestISFalse()
        client["version"].update_one({"version_str": version_str, "state": 1}, {"$set": {"is_latest": True}})
        doc = client["version"].find_one({"version_str": version_str, "state": 1},
                                         {"uid": 1, "version_str": 1, "desc": 1, "tip_way": 1})
        if doc.get("tip_way") != 1:
            sendAllUserUpateVersion(doc.get("version_str"), doc.get("desc"))
    except Exception as e:
        error = e
    finally:
        return error


def updateAllVersionLatestISFalse():
    client["version"].update({"state": 1}, {"$set": {"is_latest": False}}, multi=True)


def sendAllUserUpateVersion(version_str, desc):
    error = None
    try:
        uid = generate_uid(24)
        cursor = client["user"].find({"state": {"$in": [0, 1]}})
        for d in cursor:
            client["message"].insert(
                {
                    "uid": uid, "user_id": d.get("uid"), "push_people": "系统消息",
                    "desc": f"发现新版本V{version_str}, 请更新。版本描述：{desc}", "type": 2,
                    "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)}
            )
    except Exception as e:
        error = e
    finally:
        return error
