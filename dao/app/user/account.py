# -*- coding: utf-8 -*-
"""
@Time: 2021/1/3 15:43
@Auth: money
@File: account.py
"""
from bson.son import SON

from initialize import client


def queryBalanceChangeRecordsList(userId, category, startTime, endTime, startAmount, endAmount, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "user_id": userId, "type" if category != "all" else "null": category if category != "all" else None,
                    "$and": [{"create_time": {"$gte": startTime}}, {"create_time": {"$lte": endTime}}],
                    "state": 1
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (page - 1) * num},
            {"$limit": num},
            {"$project": {"_id": 0, "type": 1, "amount": {"$round": ["$amount", 2]}, "create_time": 1}}
        ]

        if startAmount != "" and endAmount == "":
            pipeline.insert(1, {"$match": {"amount": {"$gte": float(startAmount)}}})
        elif startAmount == "" and endAmount != "":
            pipeline.insert(1, {"$match": {"amount": {"$lte": float(endAmount)}}})
        elif startAmount != "" and endAmount != "":
            pipeline.insert(1, {"$match": {"$and": [{"amount": {"$gte": startAmount}}, {"amount": {"$lte": endAmount}}]}})
        print(pipeline)
        dataList = list(client["balance_record"].aggregate(pipeline))

    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryWorksSallStatistical(user_id):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$user_id", "browse_num": {"$sum": "$browse_num"}, "sale_num": {"$sum": "$sale_num"},
                    "comment_num": {"$sum": "$comment_num"}, "amount_num": {"$sum": "$amount"},
                    "share_num": {"$sum": "$share_num"}, "like_num": {"$sum": "$like_num"}
                }
            },
            {
                "$project": {
                    "_id": 0, "browse_num": 1, "comment_num": 1, "amount_num": 1, "share_num": 1, "like_num": 1,
                    "sale_num": 1
                }
            }
        ]
        cursor = client["user_statistical"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryWorksSaleRecords(user_id, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "state": 1}},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "uid": 1, "title": 1, "amount": 1, "create_time": 1}},
            {"$sort": SON([("create_time", -1)])}
        ]
        cursor = client["sales_records"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error
