# -*- coding: utf-8 -*-
"""
@Time: 2020/07/19 15:15:04
@File: admin_operating_api
@Auth: money
"""
import time
import datetime
from flask import request
from middleware.auth import response
from initialize import log
from initialize import client
from initialize import init_stamp
from constant import constant


def works_list_api(is_recommend):
    """
    作品列表调用接口
    :param is_recommend: 是否推荐 true推荐 false不推荐
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        type = request.args.get("type")  # 发现传default, 微图传pic, 影集传video
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if type not in ["default", "pic", "video"]:
            return response(msg="Bad Request: Params 'type' is erroe.", code=1, status=400)
        # 查询
        pipeline = [
            {
                "$match": {
                    "type" if type != "default" else "null": \
                        ({"$in": ["tp", "tj"]} if type == "pic" else "yj") if type != "default" else None,
                    "state": 2, "is_recommend": is_recommend
                }
            },
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
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"author": "$user_info.nick"}},
            {"$unset": ["user_item", "user_info"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "type": 1, "author": 1, "browse_num": 1,
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
        condition = {
            "type" if type != "default" else "null": \
                ({"$in": ["tp", "tj"]} if type == "pic" else "yj") if type != "default" else None,
            "state": 2, "is_recommend": is_recommend
        }
        count = client["works"].find(condition).count()
        data_list = [doc for doc in cursor]
        data["count"] = count
        data["list"] = data_list if data_list else []
        return data
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_platform_info(uid="001"):
    """
    平台定价信息
    :param uid: 官方定价信息uid
    """
    data = {}
    try:
        # 查询
        pipeline = [
            {"$match": {"uid": uid}},
            {
                "$project": {
                    "_id": 0, "price": 1,
                    "format": {
                        "$cond": {
                            "if": {"$eq": ["$format", "扩大授权"]},
                            "then": "k_price",
                            "else": {"$concat": [{"$toLower": "$format"}, "_price"]}
                        }
                    }
                }
            },
        ]
        cursor = client["price"].aggregate(pipeline)
        for doc in cursor:
            data.update({doc["format"]: doc["price"]})
        cursor = client["bank"].find({"state": 1})
        fees_list = [doc for doc in cursor]
        fees = fees_list[0]["fees"] if fees_list else 0
        data.update({"fees": fees})
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_platform_pricing(uid="001"):
    """
    平台定价
    :param uid: 官方定价信息uid
    """
    try:
        s_price = request.json.get("s_price")
        m_price = request.json.get("m_price")
        l_price = request.json.get("l_price")
        k_price = request.json.get("k_price")
        fees = request.json.get("fees")

        # 校验
        error = None
        if not s_price:
            error = "请输入S规格价格"
        elif not m_price:
            error = "请输入M规格价格"
        elif not l_price:
            error = "请输入L规格价格"
        elif not k_price:
            error = "请输入扩大授权规格价格"
        elif not fees:
            error = "请输入手续费"
        elif fees > 100:
            error = "手续费最高100"
        elif not any([isinstance(s_price, int), isinstance(s_price, float)]):
            error = "请输入S规格有效价格"
        elif not any([isinstance(m_price, int), isinstance(m_price, float)]):
            error = "请输入M规格有效价格"
        elif not any([isinstance(l_price, int), isinstance(l_price, float)]):
            error = "请输入L规格有效价格"
        elif not any([isinstance(k_price, int), isinstance(k_price, float)]):
            error = "请输入扩大规格有效价格"
        elif not any([isinstance(fees, int), isinstance(fees, float)]):
            error = "请输入有效的手续费"

        if error:
            return response(msg=error, code=1)

        client["price"].update({"format": "S", "uid": uid}, {"$set": {"price": float(s_price)}})
        client["price"].update({"format": "M", "uid": uid}, {"$set": {"price": float(m_price)}})
        client["price"].update({"format": "L", "uid": uid}, {"$set": {"price": float(l_price)}})
        client["price"].update({"format": "扩大授权", "uid": uid}, {"$set": {"price": float(k_price)}})
        client["bank"].update({"state": 1}, {"$set": {"fees": float(fees)}}, multi=True)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_recomm_works_list():
    """推荐作品列表"""
    try:
        data = works_list_api(True)
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_recomm_state():
    """删除推荐作品"""
    try:
        # 参数
        works_id = request.json.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        # 更新
        doc = client["works"].update({"uid": works_id}, {"$set": {"is_recommend": False}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_option_works_list():
    """作品选择列表"""
    try:
        data = works_list_api(False)
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_option_works_list_search(delta_time=30):
    """
    作品选择列表搜索
    :param delta_time: 允许查询的最大区间30天
    """
    data = {}
    try:
        # 参数
        content = request.args.get("content")
        category = request.args.get("category")  # 标题传title, 作者传author
        type = request.args.get("type")  # 发现传default, 微图传pic, 影集传video
        num = request.args.get("num")
        page = request.args.get("page")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if content and category not in ["title", "author"]:
            return response(msg="Bad Request: Params 'category' is erroe.", code=1, status=400)
        if type not in ["default", "pick", "video"]:
            return response(msg="Bad Request: Params 'type' is erroe.", code=1, status=400)
        if not start_time:
            return response(msg="Bad Request: Miss params: 'start_time'.", code=1, status=400)
        if not end_time:
            return response(msg="Bad Request: Miss params: 'end_time'.", code=1, status=400)
        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的作品", code=1)
        if len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索字数上限{constant.SEARCH_MAX}", code=1)

        pipeline = [
            {
                "$match": {
                    "type" if type != "default" else "null": \
                        ({"$in": ["tp", "tj"]} if type == "pic" else "yj") if type != "default" else None,
                    "state": 2, "is_recommend": False,
                    ("title" if category == "title" else "nick") if content else "null": \
                        {"$regex": content} if content else None,
                    "$and": [{"create_time": {"$gte": int(start_time)}}, {"create_time": {"$lte": int(end_time)}}]
                }
            },
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
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"author": "$user_info.nick"}},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "type": 1, "author": 1, "browse_num": 1,
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
        data_list = [doc for doc in cursor]
        condition = {
            "type" if type != "default" else "null": \
                ({"$in": ["tp", "tj"]} if type == "pic" else "yj") if type != "default" else None,
            "state": 2, "is_recommend": False,
            ("title" if category == "title" else "nick") if content else "null": \
                {"$regex": content} if content else None,
            "$and": [{"create_time": {"$gte": int(start_time)}}, {"create_time": {"$lte": int(end_time)}}]
        }
        count = client["works"].find(condition).count()
        data["count"] = count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_add_recomm_works(upload_max=10):
    """
    添加推荐作品
    :param upload_max: 允许同时上传作品的上限值
    """
    try:
        # 获取参数
        works_list = request.json.get("works_list")
        if not works_list:
            return response(msg="Bad Request: Miss params: 'works_list'.", code=1, status=400)
        # 最大上传10个
        if len(works_list) > upload_max:
            return response(msg=f"最多允许选择{upload_max}个作品", code=1)
        doc = client["works"].update({"uid": {"$in": works_list}}, {"$set": {"is_recommend": True}}, multi=True)
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
