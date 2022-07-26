# -*- coding: utf-8 -*-
"""
@Time: 2020/12/31 9:52
@Auth: money
@File: works.py
"""
from bson.son import SON

from initialize import client
from initialize import init_stamp
from constant import constant


def queryWorksList(category, content, state, page, num, type, startTime, endTime, sort_way):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    ("title" if category == "title" else (
                        "label" if category == "label" else "null")) if content else "null":
                        ({"$regex": content} if category == "title" else (
                            content if category == "label" else None)) if content else None,
                    "type": {"$in": ["tp", "tj"]} if type == "tj" else type,
                    "state": state if state != 8 else {"$ne": -1},
                    "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                        "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None
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
            {"$match": {
                ("nick" if category == "nick" else "null") if content else "null": (
                    {"$regex": content} if category == "nick" else None) if content else None}},
            {"$sort": SON([("create_time", int(sort_way))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}],
                    "as": "pic_temp_item"
                }
            },
            {"$addFields": {"pic_info": {"$arrayElemAt": ["$pic_item", 0]}}},
            {
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "thumb_url": {"$concat": [constant.DOMAIN, "$$item.thumb_url"]},
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "b_width": "$$item.b_width", "b_height": "$$item.b_height"
                            }
                        }
                    }
                }
            },
            {"$unset": ["user_item", "user_info", "pic_temp_item", "pic_info"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "pic_item": 1, "title": 1, "number": 1, "label": {"$slice": ["$label", 5]},
                    "type": 1, "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]}, "state": 1, "nick": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["works"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryWorksTotalNum(category, content, state, type, startTime, endTime):
    totalNum = 0
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    ("title" if category == "title" else (
                        "label" if category == "label" else "null")) if content else "null":
                        ({"$regex": content} if category == "title" else (
                            content if category == "label" else None)) if content else None,
                    "type": {"$in": ["tp", "tj"]} if type == "tj" else type,
                    "state": state if state != 8 else {"$ne": -1},
                    "$and" if startTime != 0 and endTime != 0 else "null": [{"create_time": {"$gte": startTime}}, {
                        "create_time": {"$lte": endTime}}] if startTime != 0 and endTime != 0 else None
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
            {"$match": {
                ("nick" if category == "nick" else "null") if content else "null": (
                    {"$regex": content} if category == "nick" else None) if content else None}}
        ]
        pipeline = pipeline[:6]
        pipeline.append({"$count": "count"})
        cursor = client["works"].aggregate(pipeline)
        tmp = [doc for doc in cursor]
        if tmp:
            totalNum = tmp[0]["count"]
    except Exception as e:
        error = e
    finally:
        return totalNum, error
