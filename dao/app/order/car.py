# -*- coding: utf-8 -*-
"""
@Time: 2020/12/31 20:36
@Auth: money
@File: car.py
"""
import time
from bson.son import SON

from initialize import client
from utils.util import generate_uid
from constant import constant


def carList(user_id):
    dataList = []
    error = None
    try:

        # lookup的pipeline中$match必须要使用$expr才能引用let中的字段，否则不能；如果不使用$expr，只能匹配常数
        # 查询
        pipeline = [
            {"$match": {"user_id": user_id, "state": 0}},
            {
                "$lookup": {
                    "from": "works",
                    "let": {"works_id": "$works_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$works_id"]}}}],
                    "as": "works_item"
                }
            },
            {"$addFields": {"works_info": {"$arrayElemAt": ["$works_item", 0]}}},
            {
                "$addFields": {
                    "tag": "$works_info.tag", "is_portrait": "$works_info.is_portrait",
                    "is_products": "$works_info.is_products", "price_id": "$works_info.price_id"
                }
            },
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "spec": 1, "currency": 1, "tag": 1, "is_products": 1,
                    "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}, "price": 1, "works_id": 1,
                    "is_portrait": 1
                }
            }
        ]
        cursor = client["order"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def carMergeOrder(uid_list, order):
    error = None
    try:
        client["order"].update(
            {"uid": {"$in": uid_list}},
            {"$set": {
                "order": order, "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)}},
            multi=True)
    except Exception as e:
        error = e
    finally:
        return error


def queryOrderDetail(user_id, order):
    tmp = {}
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "order": order}},
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
                    "tag": 1, "is_products": 1, "is_portrait": 1, "price": 1, "create_time": 1,
                    "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}
                }
            },
            {
                "$group": {
                    "_id": {
                        "order": "$order", "balance": "$balance", "create_time": "$create_time", "state": "$state",
                        # "tag": "$tag", "is_products": "$is_products", "is_portrait": "$is_portrait"
                    },
                    "total_amount": {"$sum": "$price"}, "works_item": {"$push": "$$ROOT"}
                }
            },
            {
                "$project": {
                    "_id": 0, "order": "$_id.order", "create_time": "$_id.create_time", "balance": "$_id.balance",
                    # "tag": "$_id.tag", "is_products": "$_id.is_products", "is_portrait": "$_id.is_portrait",
                    "state": "$_id.state", "works_item": 1, "total_amount": 1
                }
            },
            {"$sort": SON([("create_time", -1)])}
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


def queryWorksInfo(works_id):
    picId = ''
    title = ''
    priceId = 0
    error = None
    try:
        doc = client["works"].find_one({"uid": works_id, "state": 5})
        if not doc:
            raise Exception("works_id is not exists")
        picId = doc.get("pic_id")[0]
        title = doc.get("title")
        priceId = doc.get("price_id")
    except Exception as e:
        error = e
    finally:
        return picId, title, priceId, error


def queryPicInfo(pic_id, price_id, spec, works_id, user_id, is_buy):
    picURL = ''
    thumbURL = ''
    price = 0
    currency = ''
    priceUnit = ''
    error = None
    try:
        doc = client["pic_material"].find_one({"uid": pic_id})
        picURL = doc.get("pic_url")
        thumbURL = doc.get("thumb_url")

        # 规格
        doc = client["price"].find_one({"uid": price_id, "format": spec})
        price = doc.get("price")

        # 判断是否已经加入加入购物车
        temp_doc = client["order"].find_one({"works_id": works_id, "user_id": user_id, "spec": spec, "state": 0})
        if not is_buy and temp_doc:
            raise Exception("car exists")
        currency = doc.get("currency")
        priceUnit = doc.get("price_unit")

    except Exception as e:
        error = e
    finally:
        return picURL, thumbURL, price, currency, priceUnit, error


def insertOrder(user_id, works_id, title, picURL, spec, currency, priceUnit, thumbURL, price, is_buy, picId, order):
    error = None
    try:
        uid = generate_uid(24)
        condition = {
            "uid": uid, "user_id": user_id, "works_id": works_id, "title": title, "pic_url": picURL, "spec": spec,
            "currency": currency, "price_unit": priceUnit, "thumb_url": thumbURL, "price": price,
            "state": 1 if is_buy else 0, "create_time": int(time.time() * 1000), "pic_id": picId,
            "update_time": int(time.time() * 1000)
        }
        if is_buy:
            condition.update({"order": order, "order_time": int(time.time() * 1000)})
        client["order"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error
