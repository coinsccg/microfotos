# -*- coding: utf-8 -*-
"""
@Time: 2020/12/30 18:39
@Auth: money
@File: orders.py
"""
import time

from bson.son import SON

from initialize import client
from initialize import init_stamp
from constant import constant
from utils.util import generate_uid
from utils.alipay import AliPayCustomTradeAppPay
from utils.wechat import WechatPay


def queryOrderList(state, category, content, start_time, end_time, page, num):
    dataList = []
    err = None
    try:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "order": "$order", "user_id": "$user_id", "state": "$state",
                        "create_time": "$create_time", "explain": "$explain"
                    },
                    "amount": {"$sum": "$price"}
                }
            },
            {
                "$project": {
                    "_id": 0, "order": "$_id.order", "user_id": "$_id.user_id", "state": "$_id.state",
                    "create_time": "$_id.create_time", "amount": 1, "explain": "$_id.explain"
                }
            },
            {
                "$match": {
                    "state": {"$in": [-1, 1, 2, 3, 4, 5]} if state == "10" else int(state),
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
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$unset": ["user_item", "user_info"]},
            {
                "$project": {
                    "_id": 0, "order": 1, "amount": 1, "account": 1, "state": 1, "user_id": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    },
                    "explain": {"$ifNull": ["$explain", ""]}
                }
            }
        ]
        cursor = client["order"].aggregate(pipeline)
        dataList = []
        for d in cursor:
            tmp = client["trade"].find_one({"order": d.get("order")}, {"type": 1})
            payMethod = ""
            if tmp:
                payMethod = tmp.get("type")
            d["pay_method"] = payMethod
            dataList.append(d)
    except Exception as e:
        err = e
    finally:
        return dataList, err


def queryOrderTotalNum(state, category, content, start_time, end_time):
    totalNum = 0
    err = None
    try:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "order": "$order", "user_id": "$user_id", "state": "$state",
                        "create_time": "$create_time"
                    },
                    "amount": {"$sum": "$price"}
                }
            },
            {
                "$project": {
                    "_id": 0, "order": "$_id.order", "user_id": "$_id.user_id",
                    "state": "$_id.state", "create_time": "$_id.create_time", "amount": 1
                }
            },
            {
                "$match": {
                    "state": {"$gte": 1} if state == "10" else int(state),
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
            {"$count": "count"}
        ]
        cursor = client["order"].aggregate(pipeline)
        tmp = [doc for doc in cursor]
        if tmp:
            totalNum = tmp[0]["count"]
    except Exception as e:
        err = e
    finally:
        return totalNum, err


def updateOrderState():
    err = None
    try:
        cursor = client["order"].find({"state": 1})
        for doc in cursor:
            create_time = doc["create_time"]
            now_time = int(time.time() * 1000)
            if ((now_time - create_time) // 60000) >= 30:
                client["order"].update({"order": doc["order"]}, {"$set": {"state": -1}}, multi=True)
    except Exception as e:
        err = e
    finally:
        return err


def orderDetail(order):
    dataList = []
    orderInfo = {}
    count = 0
    amount = 0
    err = None
    try:
        pipeline = [
            {"$match": {"order": order}},
            {
                "$project": {
                    "_id": 0, "title": 1, "spec": 1, "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]},
                    "price": 1, "currency": 1, "order": 1, "state": 1,
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
                    }
                }
            }
        ]
        cursor = client["order"].aggregate(pipeline)
        for doc in cursor:
            if amount == 0:
                orderInfo["order"] = doc["order"]
                orderInfo["create_time"] = doc["create_time"]
                orderInfo["state"] = doc["state"]
                orderInfo["update_time"] = doc["update_time"]
            amount += doc["price"]
            dataList.append(doc)
        count = len(dataList)
    except Exception as e:
        err = e
    finally:
        return dataList, orderInfo, amount, count, err


def userInfo(userId):
    userInfo = {}
    err = None
    try:
        userInfo = client["user"].find_one({"uid": userId}, {"_id": 0, "nick": 1, "account": 1, "mobile": 1})
    except Exception as e:
        err = e
    finally:
        return userInfo, err


def rejectRefundSendMessage(userId, reason, order):
    error = None
    try:
        # 给用户发送消息
        uid = generate_uid(24)
        client["message"].insert(
            {
                "uid": uid, "user_id": userId, "push_people": "系统消息",
                "desc": "您的退款申请被驳回，原因是：" + str(reason), "type": 1,
                "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
        )
        # 退款失败更新状态
        client["order"].update({"order": order}, {"$set": {"state": 5}}, multi=True)
    except Exception as e:
        error = e
    finally:
        return error


def sendRefundRequest(order, userId):
    error = None
    try:
        amount, _, error = queryRefundAmount(order)
        if error:
            raise Exception(error)

        tmp = client["trade"].find_one({"order": order})
        payMethod = tmp["type"]

        if payMethod == "balance":
            error = refundFollowUpoperation(order, userId, amount, "balance")
            if error:
                raise Exception(error)
        elif payMethod == "alipay":
            alipay = AliPayCustomTradeAppPay(order, amount)
            tmp, res = alipay.refund_trade_app_pay_request()
            if not tmp:
                raise Exception(res)
            out_trade_no = res["out_trade_no"]
            total_amount = res["refund_fee"]
            tmp = list(client["order"].find({"order": out_trade_no, "state": 4}))
            if not tmp:
                raise Exception("out_trade_no is not exists")

            userId = tmp[0]["user_id"]
            error = refundFollowUpoperation(out_trade_no, userId, total_amount)
            if error:
                raise Exception(f"{out_trade_no} alipay refund success follow operation failed")
        elif payMethod == "wxpay":
            refundNo = generate_uid(24)
            wechat = WechatPay(order, int(amount * 100))
            error = wechat.wechat_refund_request(refundNo, int(amount * 100))
            if error:
                raise Exception("wechat refund failed")

    except Exception as e:
        error = e
    finally:
        return error


def refundFollowUpoperation(order, userId, amount, payMethod=None):
    error = None
    try:
        cursor = client["order"].find({"order": order, "state": 4})
        # 余额购买的商品退款才需要退款记录
        tmp1 = client["user"].find_one({"uid": userId}, {"_id": 0, "balance": 1})
        if payMethod:
            # 买家余额记录
            condition = {
                "user_id": userId, "type": "退款", "order": order, "amount": float(amount),
                "balance": tmp1.get("balance") + float(amount), "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["balance_record"].insert(condition)
            # 买家余额变更
            client["user"].update({"uid": userId}, {"$inc": {"balance": float(amount)}})
        # 买家消息记录
        error = sendMessage(userId, "您的退款申请已同意，退款金额将在24小时内到达您的第三方账户。")
        if error:
            raise Exception(error)

        # 买家商品变更
        temp = {}
        for i in cursor:
            worksId = i["works_id"]
            doc1 = client["works"].find_one({"uid": worksId}, {"_id": 0, "user_id": 1})
            sellerId = doc1["user_id"]
            if sellerId in temp:
                p = temp[sellerId]
                temp[sellerId] = p + i["price"]
            else:
                temp[sellerId] = i["price"]
            # 买家商品变更
            doc2 = client["goods"].find_one({"works_id": i["works_id"], "user_id": userId, "state": 1})
            if not doc2:
                raise Exception("order is not exists")
            spec = doc2["spec"]
            tmpSpec = i["spec"]
            if tmpSpec in spec:
                spec.remove(tmpSpec)
            if not spec:
                client["goods"].update_one({"works_id": i["works_id"], "user_id": userId, "state": 1},
                                           {"$set": {"state": -1}})
                continue
            client["goods"].update_one({"works_id": i["works_id"], "user_id": i["user_id"], "state": 1},
                                       {"$set": {"spec": spec}})

        # 卖家余额变更及余额记录
        for i in temp.keys():
            totalFee = temp[i]
            doc3 = client["user"].find_one({"uid": i}, {"_id": 0, "balance": 1})
            # 卖家余额变更
            client["user"].update({"uid": i}, {"$inc": {"balance": -float(totalFee)}})
            # 卖家余额记录
            doc4 = {
                "user_id": i, "type": "退款", "order": order, "amount": -float(totalFee),
                "balance": doc3.get("balance") - float(totalFee), "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["balance_record"].insert(doc4)
            # 卖家消息推送
            # error = sendMessage(i, "")
            # if error:
            #     raise Exception(error)

        # 订单状态改变
        client["order"].update({"order": order, "state": 4}, {"$set": {"state": 3}})
    except Exception as e:
        error = e
    finally:
        return error


def queryRefundAmount(order):
    amount = 0
    error = None
    payMethod = ""
    try:
        cursor = client["order"].find({"order": order, "state": 4},
                                      {"spec": 1, "works_id": 1, "user_id": 1, "price": 1})
        amount = 0
        for d in cursor:
            amount += d["price"]

        tmp = client["trade"].find_one({"order": order, "state": 1}, {"type": 1})
        payMethod = tmp.get("type")
    except Exception as e:
        error = e
    finally:
        return amount, payMethod, error


def sendMessage(userId, desc):
    error = None
    try:
        uid = generate_uid(24)
        client["message"].insert(
            {"uid": uid, "user_id": userId, "push_people": "系统消息", "desc": desc, "type": 1,
             "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)})
    except Exception as e:
        error = e
    finally:
        return error
