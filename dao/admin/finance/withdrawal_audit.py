# -*- coding: utf-8 -*-
"""
@Time: 2020/12/30 19:01
@Auth: money
@File: withdrawal_audit.py
"""
import time
from bson.son import SON

from initialize import init_stamp
from initialize import client


def queryWithdrawalAuditList(category, content, start_time, end_time, channel, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "state": 1,
                    "$and": [{"create_time": {"$gte": int(start_time)}}, {"create_time": {"$lte": int(end_time)}}],
                    "order" if category == "order" and content else "null": \
                        {"$regex": content} if category == "order" and content else None,
                    "channel" if channel != "default" else "null": channel if channel != "default" else None
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
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$unset": ["user_item", "user_info"]},
            {
                "$project": {
                    "_id": 0, "order": 1, "amount": 1, "account": 1, "trade_name": 1, "trade_id": 1, "channel": 1,
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


def queryWithdrawalAuditTotalNum(category, content, start_time, end_time, channel):
    totalNum = 0
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "state": 1,
                    "$and": [{"create_time": {"$gte": int(start_time)}}, {"create_time": {"$lte": int(end_time)}}],
                    "order" if category == "order" and content else "null": \
                        {"$regex": content} if category == "order" and content else None,
                    "channel" if channel != "default" else "null": channel if channel != "default" else None
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
            {"$addFields": {"user_account": "$user_info.account"}},
            {
                "$match": {
                    "account" if category == "account" and content else "null": \
                        {"$regex": content} if category == "account" and content else None
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


def withdrawalAudit(order_list, state):
    error = None
    try:
        client["withdrawal_records"].update(
            {"order": {"$in": order_list}},
            {"$set": {"state": state}},
            multi=True
        )

        for i in order_list:
            # 用户余额减少
            doc = client["withdrawal_records"].find_one({"order": i})
            if state == 2:
                client["user"].update({"uid": doc["user_id"]},
                                      {"$inc": {"balance": -doc["amount"]}})

            # 提现记录
            temp = client["user"].find_one({"uid": doc["user_id"]}, {"_id": 0, "balance": 1, "uid": 1})

            if state == 2:
                if doc["channel"] == "支付宝":
                    tmpType = "支付宝提现"
                else:
                    tmpType = "银行卡提现"
                condition = {
                    "user_id": doc["user_id"], "type": tmpType, "order": i,
                    "amount": -doc["amount"], "balance": temp["balance"], "state": 1,
                    "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
                client["balance_record"].insert(condition)
            # 提现解冻记录
            condition = {
                "user_id": doc["user_id"], "type": "取消冻结", "order": i,
                "amount": abs(doc["amount"]), "balance": temp["balance"] + abs(doc["amount"]), "state": 1,
                "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
            client["balance_record"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def withdrawalAuditListExport(category, content, order_list, start_time, end_time, channel):
    dataList = None
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "order" if order_list else "null": {"$in": order_list} if order_list else None,
                    "state": 1,
                    "$and": [{"create_time": {"$gte": int(start_time)}}, {"create_time": {"$lte": int(end_time)}}],
                    "order" if category == "order" and content else "null": \
                        {"$regex": content} if category == "order" and content else None,
                    "channel" if channel != "default" else "null": channel if channel != "default" else None
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
                    "_id": 0, "order": 1, "amount": 1, "account": 1, "trade_name": 1, "trade_id": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    },
                    "channel": 1
                }
            }
        ]
        cursor = client["withdrawal_records"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error
