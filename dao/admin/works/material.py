# -*- coding: utf-8 -*-
"""
@Time: 2020/12/31 9:32
@Auth: money
@File: material.py
"""
from bson.son import SON

from initialize import client
from initialize import init_stamp
from constant import constant


def queryMaterialList(category, content, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "state": 1,
                    ("title" if category == "title" else ("label" if category == "label" else "null")) if content \
                        else "null": (
                        {"$regex": content} if category == "title" else (content if category == "label" else None)
                    ) if content else None
                }
            },
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick"}},
            {
                "$match": {
                    ("nick" if category == "nick" else "null") if content \
                        else "null": ({"$regex": content} if category == "nick" else None) if content else None
                }
            },
            {"$unset": ["user_item", "user_info"]},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "label": 1, "nick": 1,
                    "create_time": {"$dateToString": {"format": "%Y-%m-%d %H:%M",
                                                      "date": {"$add": [init_stamp, "$create_time"]}}},
                    "big_pic_url": {"$concat": [constant.DOMAIN, "$big_pic_url"]}
                }
            }
        ]
        cursor = client["pic_material"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryMaterialTotalNum(category, content):
    totalNum = 0
    error = None
    try:
        condition = [
            {
                "$match": {
                    "state": 1,
                    ("title" if category == "title" else ("label" if category == "label" else "null")) if content \
                        else "null": ({"$regex": content} if category == "title" else (content if category == "label" \
                                                                                           else None)) if content else None
                }
            },
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick"}},
            {
                "$match": {
                    ("nick" if category == "nick" else "null") if content \
                        else "null": ({"$regex": content} if category == "nick" else None) if content else None
                }
            },
            {"$count": "count"}
        ]
        cursor = client["pic_material"].aggregate(condition)
        tmp = [doc for doc in cursor]
        if tmp:
            totalNum = tmp[0]["count"]
    except Exception as e:
        error = e
    finally:
        return totalNum, error


def queryMaterialDetail(pic_id):
    dataList = []
    error = None
    try:
        # 查询
        pipeline = [
            {"$match": {"uid": pic_id}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick", "account": "$user_info.account"}},
            {"$unset": ["user_item", "user_info"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "label": 1, "nick": 1, "account": 1, "format": 1,
                    "size": 1, "create_time": {"$dateToString": {"format": "%Y-%m-%d %H:%M",
                                                                 "date": {"$add": [init_stamp, "$create_time"]}}},
                    "big_pic_url": {"$concat": [constant.DOMAIN, "$big_pic_url"]}
                }
            }
        ]
        cursor = client["pic_material"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryMaterialSpec(pic_id):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"pic_id": pic_id, "state": 1}},
            {"$project": {"_id": 0, "format": 1, "pic_url": {"$concat": [constant.DOMAIN, "$pic_url"]}}}
        ]
        cursor = client["price"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def putMaterial(pic_id, title):
    error = None
    try:
        client["pic_material"].update({"uid": pic_id}, {"$set": {"title": title}})
    except Exception as e:
        error = e
    finally:
        return error
