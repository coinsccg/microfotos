# -*- coding: utf-8 -*-
"""
@Time: 2020/12/30 18:39
@Auth: money
@File: withdrawal.py
"""
from bson.son import SON

from initialize import init_stamp
from initialize import client


def queryWithdrawalList(category, content, state, start_time, end_time, page, num):
    dataList = []
    error = None
    try:

        pipeline = [
            {
                "$match": {
                    "state": int(state),
                    "$and": [{"create_time": {"$gte": int(start_time)}}, {"create_time": {"$lte": int(end_time)}}],
                    "order" if (category == "order" and content) else "null": \
                        {"$regex": content} if (category == "order" and content) else None
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
            {"$addFields": {"account": "$user_info.account"}},
            {
                "$match": {
                    "account" if (category == "account" and content) else "null": \
                        {"$regex": content} if (category == "account" and content) else None
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$unset": ["user_item", "user_info"]},
            {
                "$project": {
                    "_id": 0, "order": 1, "amount": 1, "account": 1,
                    "channel": 1, "state": 1, "trade_name": 1, "trade_id": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    },
                    "update_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$update_time"]}
                        }
                    },
                }
            }
        ]
        cursor = client["withdrawal_records"].aggregate(pipeline)
        dataList = [doc for doc in cursor]

    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryWithdrawalTotalNum(category, content, state, start_time, end_time):
    totalNum = 0
    error = None
    try:

        pipeline = [
            {
                "$match": {"state": int(state),
                           "$and": [{"create_time": {"$gte": int(start_time)}},
                                    {"create_time": {"$lte": int(end_time)}}],
                           "order" if (category == "order" and content) else "null": \
                               {"$regex": content} if (category == "order" and content) else None
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
            {"$addFields": {"account": "$user_info.account"}},
            {
                "$match": {
                    "account" if category == "account" and content else "null": \
                        {"$regex": content} if (category == "account" and content) else None
                }
            },
            {"$count": "count"}
        ]
        cursor = client["withdrawal_records"].aggregate(pipeline)
        tmp = [doc for doc in cursor]
        if tmp:
            totalNum = tmp[0]["count"]
    except Exception as e:
        error = e
    finally:
        return totalNum, error


def queryWithdrawalListExport(category, content, state, start_time, end_time):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "state": int(state),
                    "$and": [{"create_time": {"$gte": int(start_time)}}, {"create_time": {"$lte": int(end_time)}}],
                    "order" if category == "order" and content else "null": \
                        {"$regex": content} if category == "order" and content else None
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
            {"$addFields": {"account": "$user_info.account"}},
            {
                "$match": {
                    "account" if category == "account" and content else "null": \
                        {"$regex": content} if category == "account" and content else None
                }
            },
            {"$unset": ["user_item", "user_info"]},
            {"$sort": SON([("create_time", -1)])},
            {
                "$project": {
                    "_id": 0, "order": 1, "amount": 1, "account": 1, "trade_name": 1, "trade_id": 1, "channel": 1,
                    "state": {"$cond": {"if": {"$eq": ["$state", 0]}, "then": "驳回", "else": "完成"}},
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    },
                }
            }
        ]
        cursor = client["withdrawal_records"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error
