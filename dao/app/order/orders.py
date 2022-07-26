# -*- coding: utf-8 -*-
"""
@Time: 2020/12/31 15:42
@Auth: money
@File: orders.py
"""
import time
import datetime
import base64
import random
from bson.son import SON

from initialize import init_stamp
from initialize import client
from utils.util import generate_uid
from constant import constant


def add_user_goods_api(order, buyer_id):
    """
    添加到用户商品
    :param order: 商品订单
    :param buyer_id: 买家id
    """
    error = None
    try:
        cursor = client["order"].find({"order": order})
        data1 = {}
        for doc in cursor:
            if doc["works_id"] not in data1:
                data1[doc["works_id"]] = [doc["spec"]]
            else:
                temp = data1[doc["works_id"]]
                temp.append(doc["spec"])
                data1[doc["works_id"]] = list(set(temp))
        works_id_list = list(data1.keys())
        data2 = {}
        cursor = client["works"].find({"uid": {"$in": works_id_list}})
        for doc in cursor:
            data2[doc["uid"]] = doc["pic_id"][0]
        uid = generate_uid(24)
        condition = []
        for i in works_id_list:
            doc = client["goods"].find_one({"user_id": buyer_id, "works_id": i, "pic_id": data2[i], "state": 1})
            if doc:
                spec = list(set(doc["spec"] + data1[i]))
                client["goods"].update({"user_id": buyer_id, "works_id": i, "state": 1},
                                       {"$set": {"spec": spec}})

            else:
                temp = {
                    "uid": uid, "user_id": buyer_id, "works_id": i, "pic_id": data2[i], "spec": data1[i],
                    "order": order, "state": 1, "create_time": int(time.time() * 1000),
                    "update_time": int(time.time() * 1000)
                }
                condition.append(temp)

        if condition:
            client["goods"].insert_many(condition)
    except Exception as e:
        error = e
    finally:
        return error


def statistical_day_amount_api(data_list):
    """
    统计日收入
    :param data_list: 订单商品列表
    """
    error = None
    try:
        # today时间戳
        today = datetime.date.today()
        today_stamp = int(time.mktime(today.timetuple()) * 1000)
        for i in data_list:
            temp = client["works"].find_one({"uid": i["works_id"]})
            doc = client["user_statistical"].find_one({"user_id": temp["user_id"], "date": today_stamp})
            if doc:
                client["user_statistical"].update(
                    {"user_id": temp["user_id"], "date": today_stamp},
                    {"$inc": {"amount": i["price"], "sale_num": 1}}
                )
            else:
                condition = {
                    "user_id": temp["user_id"], "date": today_stamp, "works_num": 0, "sale_num": 1, "browse_num": 0,
                    "amount": i["price"], "like_num": 0, "goods_num": 0, "register_num": 0, "comment_num": 0,
                    "share_num": 0, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
                client["user_statistical"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def sales_records_api(data_list):
    """销售记录api
    :param data_list: 订单商品列表
    """
    error = None
    try:
        for i in data_list:
            temp = client["works"].find_one({"uid": i["works_id"]})
            doc = client["sales_records"].find_one(
                {"user_id": temp["user_id"], "order": i["order"], "works_id": i["works_id"], "state": 1}
            )
            if doc:
                client["sales_records"].update(
                    {"user_id": temp["user_id"], "order": i["order"], "works_id": i["works_id"]},
                    {"$inc": i["price"]}
                )
            else:
                uid = generate_uid(24)
                condition = {
                    "uid": uid, "user_id": temp["user_id"], "order": i["order"], "works_id": i["works_id"],
                    "title": temp["title"], "pic_url": i["pic_url"], "amount": i["price"], "state": 1,
                    "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
                client["sales_records"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def queryOrderState(order):
    rest = False
    error = None
    try:
        tmp = client["order"].find({"order": order})
        for d in tmp:
            if d["state"] == 2:
                rest = True
                break
    except Exception as e:
        error = e
    finally:
        return rest, error


def updateOrderRefund(order, explain):
    error = None
    try:
        client["order"].update({"order": order, "state": 2}, {"$set": {"explain": explain, "state": 4}}, multi=True)
    except Exception as e:
        error = e
    finally:
        return error


def queryOrderTotalAmount(order, user_id):
    goodId = ""
    totalAmount = 0
    balance = 0
    error = None
    try:
        totalAmount = 0
        cursor = client["order"].find({"order": order, "state": 1})
        n = 0
        for doc in cursor:
            totalAmount += doc["price"]
            if n == 0:
                goodId = doc["works_id"]
                n += 1
        doc = client["user"].find_one({"uid": user_id})
        balance = doc.get("balance")
    except Exception as e:
        error = e
    finally:
        return goodId, totalAmount, balance, error


def tradeRecords(trade_id, goods_id, order, total_amount, pay_method):
    error = None
    try:
        # 生成交易信息

        condition = {
            "trade_id": trade_id, "goods_id": goods_id, "state": 1, "order": order, "trade_amount": total_amount,
            "type": "balance" if pay_method == "余额" else ("alipay" if pay_method == "支付宝" else "wxpay"),
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }
        client["trade"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def verifyBlancePayPassword(userId, password):
    balance = 0
    error = None
    try:
        doc = client["user"].find_one({"uid": userId, "password": password})
        if not doc:
            raise Exception("密码错误")
        balance = doc["balance"]
    except Exception as e:
        error = e
    finally:
        return balance, error


def queryTradeAmountAndOrder(trade_id):
    tradeAmount = 0
    order = ""
    error = None
    try:
        tmp = client["trade"].find_one({"trade_id": trade_id})
        tradeAmount = tmp["trade_amount"]
        order = tmp["order"]
    except Exception as e:
        error = e
    finally:
        return tradeAmount, order, error


def judgeIsOwnWorks(order, useId, trade_amount):
    dataList = []
    error = None
    try:
        cursor = client["order"].find({"order": order, "state": 1})
        dataList = [doc for doc in cursor]
        works_id_list = [i["works_id"] for i in dataList]
        cursor = client["works"].find({"uid": {"$in": works_id_list}})
        seller_id_list = list(set([doc["user_id"] for doc in cursor]))
        tmp = client["user"].find_one({"uid": useId}, {"_id": 0, "balance": 1})
        if useId in seller_id_list:
            raise Exception("自己不能购买自己的商品")
        if tmp.get("balance") < trade_amount:
            raise Exception("余额不足")
    except Exception as e:
        error = e
    finally:
        return dataList, error


def orderPaySuccessFollowOperation(out_trade_no, user_id, data_list, totalAmount=None):
    """支付成功后续操作"""
    error = None
    try:
        # 余额购买商品才需要变更买家的余额
        if totalAmount:
            # 买家余额变更
            doc0 = client["user"].find_one({"uid": user_id}, {"_id": 0, "balance": 1, "uid": 1})
            client["user"].update({"uid": user_id}, {"$inc": {"balance": -totalAmount}})
            # 买家余额记录变更
            condition = {
                "user_id": user_id, "type": "消费", "order": out_trade_no, "amount": -float(totalAmount),
                "balance": doc0["balance"] - float(totalAmount), "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["balance_record"].insert(condition)

        # 卖家余额变更及作品销量变更
        temp = {}
        for i in data_list:
            doc1 = client["works"].find_one({"uid": i["works_id"]})
            sellerId = doc1["user_id"]
            if sellerId in temp:
                p = temp[sellerId]
                temp[sellerId] = p + i["price"]
            else:
                temp[sellerId] = i["price"]
            # 作品销量变更
            client["works"].update_one({"uid": i["works_id"]}, {"$inc": {"sale_num": 1}})
            # 卖家余额变更
            client["user"].update({"uid": sellerId}, {"$inc": {"balance": i["price"]}})

        # 卖家余额记录变更
        for i in temp.keys():
            doc2 = client["user"].find_one({"uid": i}, {"_id": 0, "balance": 1, "uid": 1})
            condition = {
                "user_id": i, "type": "售卖", "order": out_trade_no, "amount": float(temp[i]),
                "balance": doc2["balance"], "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["balance_record"].insert(condition)

        # 将商品添加到用户图片库
        add_user_goods_api(out_trade_no, user_id)

        # 统计日收入
        statistical_day_amount_api(data_list)

        # 统计卖家销售记录
        sales_records_api(data_list)

        # 支付完成
        client["order"].update({"order": out_trade_no, "state": 1}, {"$set": {"state": 2}}, multi=True)
    except Exception as e:
        error = e
    finally:
        return error


def verifyPicIsBuy(order):
    deltaAmount = 0
    excludeAmount = 0
    error = None
    try:
        cursor = client["order"].find({"order": order})
        exclude = []
        total_amount = 0
        verify = 0
        for i in cursor:
            doc = client["order"].find_one(
                {
                    "works_id": i["works_id"], "user_id": i["user_id"], "spec": i["spec"], "order": {"$ne": order},
                    "state": 2
                }
            )
            if doc:
                exclude.append(doc)
                client["order"].update_one(
                    {"order": order, "works_id": i["works_id"], "spec": i["spec"], "state": 1},
                    {"$set": {"state": -2}}
                )
            total_amount += i["price"]
            verify += 1
        if verify == 0:
            raise Exception("order is not exists")
        excludeAmount = 0
        for doc in exclude:
            excludeAmount += doc["price"]
        deltaAmount = total_amount - excludeAmount
    except Exception as e:
        error = e
    finally:
        return deltaAmount, excludeAmount, error


def queryOrderInfo(user_id, order):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "order": order, "state": -2}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {
                "$lookup": {
                    "from": "works",
                    "let": {"works_id": "$works_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$works_id"]}}}],
                    "as": "works_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "works_info": {"$arrayElemAt": ["$works_item", 0]}
                }
            },
            {"$addFields": {"balance": "$user_info.balance", "tag": "$works_info.tag"}},
            {"$unset": ["user_item", "user_info", "works_info", "works_item"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "order": 1, "title": 1, "spec": 1, "balance": 1, "currency": 1, "state": 1,
                    "tag": 1, "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}, "price": 1, "update_time": 1,
                    "create_time": 1
                }
            }
        ]
        cursor = client["order"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryOrderDetail(user_id, order):
    error = None
    tmp = {}
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "order": order}},  # "state": {"$ne": -2}
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {
                "$lookup": {
                    "from": "works",
                    "let": {"works_id": "$works_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$works_id"]}}}],
                    "as": "works_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "works_info": {"$arrayElemAt": ["$works_item", 0]}
                }
            },
            {
                "$addFields": {
                    "balance": "$user_info.balance", "tag": "$works_info.tag", "is_portrait": "$works_info.is_portrait",
                    "is_products": "$works_info.is_products"
                }
            },
            {"$unset": ["user_item", "user_info", "works_info", "works_item"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "order": 1, "title": 1, "spec": 1, "currency": 1, "balance": 1, "state": 1,
                    "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}, "price": 1, "update_time": 1,
                    "create_time": 1, "tag": 1, "is_portrait": 1, "is_products": 1
                }
            },
            {
                "$group": {
                    "_id": {"order": "$order", "create_time": "$create_time", "state": "$state", "balance": "$balance"},
                    "total_amount": {"$sum": "$price"}, "works_item": {"$push": "$$ROOT"}
                }
            },
            {
                "$project": {
                    "_id": 0, "order": "$_id.order", "create_time": "$_id.create_time", "works_item": 1,
                    "total_amount": 1, "state": "$_id.state", "balance": {"$round": ["$_id.balance", 2]}
                }
            }
        ]
        cursor = client["order"].aggregate(pipeline)
        for doc in cursor:
            create_time = doc["create_time"]
            now_time = int(time.time() * 1000)
            doc["delta_time"] = (create_time + 1800000 - now_time) // 1000
            tmp = doc
    except Exception as e:
        error = e
    finally:
        return tmp, error


def updateOrderState(user_id):
    error = None
    try:
        cursor = client["order"].find({"user_id": user_id, "state": 1})
        for doc in cursor:
            create_time = doc["create_time"]
            now_time = int(time.time() * 1000)
            if ((now_time - create_time) // 60000) >= 30:
                client["order"].update({"order": doc["order"]}, {"$set": {"state": -1}}, multi=True)
    except Exception as e:
        error = e
    finally:
        return error


def queryOrderList(user_id, is_complete, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "state": {"$in": [-1, 2, 5, 4, 3]} if is_complete == "true" else 1}},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {
                "$lookup": {
                    "from": "works",
                    "let": {"works_id": "$works_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$works_id"]}}}],
                    "as": "works_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "works_info": {"$arrayElemAt": ["$works_item", 0]}
                }
            },
            {
                "$addFields": {
                    "balance": "$user_info.balance", "tag": "$works_info.tag", "is_portrait": "$works_info.is_portrait",
                    "is_products": "$works_info.is_products"
                }
            },
            {"$unset": ["user_item", "user_info", "works_info", "works_item"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "order": 1, "title": 1, "spec": 1, "balance": 1, "currency": 1, "state": 1,
                    "tag": 1, "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}, "price": 1, "update_time": 1,
                    "create_time": 1, "is_portrait": 1, "is_products": 1
                }
            },
            {
                "$group": {
                    "_id": {"order": "$order", "create_time": "$create_time", "state": "$state", "balance": "$balance"},
                    "total_amount": {"$sum": "$price"}, "works_item": {"$push": "$$ROOT"}
                }
            },
            {
                "$project": {
                    "_id": 0, "order": "$_id.order", "create_time": "$_id.create_time", "works_item": 1,
                    "total_amount": 1, "balance": "$_id.balance", "state": "$_id.state"
                }
            },
            {"$sort": SON([("create_time", -1)])},
        ]
        cursor = client["order"].aggregate(pipeline)
        if is_complete == "false":
            for doc in cursor:
                create_time = doc["create_time"]
                now_time = int(time.time() * 1000)
                doc["delta_time"] = (create_time + 1800000 - now_time) // 1000
                dataList.append(doc)
        else:
            dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryUnpaidOrderNum(user_id):
    count = 0
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "state": 1}},
            {"$group": {"_id": "$order"}},
            {"$count": "count"},
        ]
        cursor = client["order"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        count = data_list[0]["count"] if data_list else 0
    except Exception as e:
        error = e
    finally:
        return count, error


def updateCancelOrder(order_id, user_id):
    error = None
    try:
        # 更新
        client["order"].update(
            {"order": order_id, "user_id": user_id, "state": 1},
            {"$set": {"state": -1, "update_time": 1}},
            multi=True
        )
    except Exception as e:
        error = e
    finally:
        return error


def getUser(uid):
    error = None
    user = {}
    try:
        pipeline = [
            {"$match": {"uid": uid}},
            {"$project": {"mobile": 1, "password": 1}}
        ]
        cursor = client["user"].aggregate(pipeline)
        user = [doc for doc in cursor][0]
    except Exception as e:
        error = e
    finally:
        return user, error
