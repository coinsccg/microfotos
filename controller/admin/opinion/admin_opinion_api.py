# -*- coding: utf-8 -*-
"""
@Time: 2020/07/19 16:31:50
@File: admin_opinion_api
@Auth: money
"""
import time
import datetime
from bson.son import SON
from flask import request
from middleware.auth import response
from utils.util import generate_uid
from constant import constant
from initialize import log
from initialize import client
from initialize import init_stamp


def get_report_comment_search(delta_time=30):
    """
    举报评论列表搜索
    :param: search_max: 搜索内容上限字符数
    :param delta_time: 允许查询的最大区间30天
    """
    data = {}
    try:

        # 获取参数
        num = request.args.get("num")
        page = request.args.get("page")
        content = request.args.get("content")
        state = request.args.get("state")  # 正常评论传1， 举报评论传0
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")

        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容上限{constant.SEARCH_MAX}个字符", code=1)

        if state == "1":
            if not start_time:
                return response(msg="Bad Request: Miss params: 'start_time'.", code=1, status=400)
            if not end_time:
                return response(msg="Bad Request: Miss params: 'end_time'.", code=1, status=400)
            start_time = start_time + " 00:00:00"
            end_time = end_time + " 23:59:59"
            timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
            end_time = int(time.mktime(timeArray2.timetuple()) * 1000)
            if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
                return response(msg=f"最多可连续查询{delta_time}天以内的评论", code=1)

        # 被举报评论的id
        temp = client["comment_report"].find({"state": 1})
        comment_report_id = [doc["comment_id"] for doc in temp]

        pipeline = [
            {
                "$match": {
                    "state" if state == "1" else "uid": int(state) if state == "1" else {"$in": comment_report_id},
                    "content" if content else "null": {"$regex": content} if content else None
                }
            },
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
            {"$addFields": {"user_account": "$user_info.account", "works_title": "$works_info.title"}},
            {
                "$project": {
                    "_id": 0, "uid": 1, "user_account": 1, "works_title": 1, "content": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        if state == "1":
            pipeline[0]["$match"].update(
                {
                    "$and": [
                        {"create_time": {"$gte": int(start_time)}},
                        {"create_time": {"$lte": int(end_time)}}
                    ]
                }
            )
        cursor = client["comment"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        # 总数
        count = client["comment"].find(pipeline[0]["$match"]).count()
        data["count"] = count if state == "1" else len(comment_report_id)
        data["list"] = data_list
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_report_comment_state(option_max=10):
    """
    审核举报评论
    :param option_max: 最多允许选择的个数
    """
    try:
        # 参数
        comment_list = request.json.get("comment_list")  # array
        state = request.json.get("state")  # -1删除，1标记正常
        if not comment_list:
            return response(msg="Bad Request: Miss params: 'comment_list'.", code=1, status=400)
        if len(comment_list) > option_max:
            return response(msg=f"最多允许选择{option_max}条评论", code=1)
        if state not in [-1, 1]:
            return response(msg="Bad Request: Params 'state' is erroe.", code=1, status=400)
        client["comment_report"].update({"comment_id": {"$in": comment_list}}, {"$set": {"state": -1}}, multi=True)
        doc = client["comment"].update(
            {"uid": {"$in": comment_list}},
            {"$set": {"state": int(state)}},
            multi=True
        )
        doc = client["like_records"].update(
            {"comment_id": {"$in": comment_list}},
            {"$set": {"state": int(state)}},
            multi=True
        )
        # 删除评论时，相应减少works中comment_num
        if state == -1:
            cursor = client["comment"].find({"uid": {"$in": comment_list}}, {"_id": 0, "works_id": 1})
            works_id_list = [doc["works_id"] for doc in cursor]
            works_id_list = list(set(works_id_list))
            doc = client["works"].update({"uid": {"$in": works_id_list}}, {"$inc": {"comment_num": -1}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_report_comment_top():
    """评论相关统计"""
    data = {}
    try:
        # 敏感词数
        bad_count = client["bad"].find({"state": 1}).count()
        # 今日新增评论
        before_dawn = datetime.datetime.now().date()
        before_dawn_timestamp = int(time.mktime(before_dawn.timetuple())) * 1000
        now_timestamp = int(time.time() * 1000)
        pipeline = [
            {
                "$match": {
                    "state": 1,
                    "$and": [
                        {"create_time": {"$gte": before_dawn_timestamp}},
                        {"create_time": {"$lte": now_timestamp}}
                    ]
                }
            },
            {"$count": "count"}
        ]
        cursor = client["comment"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        normal_count = data_list[0]["count"] if data_list else 0
        # 举报评论
        report_count = client["comment_report"].find({"state": 1}).count()
        data["report_count"] = report_count
        data["normal_count"] = normal_count
        data["bad_count"] = bad_count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_bad_keyword_list():
    """敏感词列表"""
    try:
        # 查询
        cursor = client["bad"].find({"state": 1})
        data_list = [doc["keyword"] for doc in cursor]
        data_str = "、".join(data_list)
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def post_add_bad_keyword():
    """增加敏感词"""
    try:
        # 参数
        content = request.json.get("content")
        if content:
            keyword_list = content.split("、")
            temp_list = []
            for i in keyword_list:
                uid = generate_uid(24)
                obj = {"keyword": i, "state": 1}
                temp_list.append(obj)
            client["bad"].drop()
            client["bad"].insert_many(temp_list)
        else:
            client["bad"].update_many({}, {"$set": {"state": -1}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_works_report_number():
    """作品举报数据"""
    try:

        # 同步作品状态
        tmpCursor = client["works_report"].find({"state": 1})
        for doc in tmpCursor:
            tmpW = client["works"].find_one({"uid": doc.get("works_id")})
            if tmpW.get("state") not in [2, 5]:
                client["works_report"].update({"works_id": doc.get("works_id"), "state": 1}, {"$set": {"state": -1}})

        pipeline = [
            {"$match": {"state": 1}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
            {"$project": {"_id": 0, "type": "$_id", "count": 1}}
        ]
        cursor = client["works_report"].aggregate(pipeline)
        tj_num = 0
        yj_num = 0
        tw_num = 0
        for doc in cursor:
            if doc["type"] == "yj":
                yj_num += doc["count"]
            elif doc["type"] == "tw":
                tw_num += doc["count"]
            else:
                tj_num += doc["count"]
        data = {}
        data["tj_num"] = tj_num
        data["tw_num"] = tw_num
        data["yj_num"] = yj_num

        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0修改
def get_report_works_list(domain=constant.DOMAIN):
    """
    被举报图集/图文/影集作品接口
    :param domain: 域名
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        type = request.args.get("type")  # 图集传tj, 图文传tw, 影集传yj
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if type not in ["tj", "tw", "yj"]:
            return response(msg="Bad Request: Params 'type' is error.", code=1, status=400)

        # 查询被举报作品id
        cursor = client["works_report"].find(
            {"type": type if type != "tj" else {"$in": ["tj", "tp"]}, "state": 1},
            {"_id": 0, "works_id": 1, "create_time": 1}, sort=[("create_time", -1)]
        ).skip((int(page) - 1) * int(num)).limit(int(num))
        report_works = []
        report_id_list = []
        for c in cursor:
            report_works.append(c)
            report_id_list.append(c["works_id"])

        # 查询
        pipeline = [
            {"$match": {"uid": {"$in": report_id_list}}},
            {"$match": {"state": {"$in": [2, 5]}}},
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
                                "thumb_url": {"$concat": [domain, "$$item.thumb_url"]},
                                "big_pic_url": {"$concat": [domain, "$$item.big_pic_url"]},
                                "b_width": "$$item.b_width", "b_height": "$$item.b_height"
                            }
                        }
                    }
                }
            },
            {"$unset": ["user_item", "user_info", "pic_temp_item", "pic_info"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "pic_item": 1, "title": 1, "number": 1, "label": 1, "type": 1,
                    "cover_url": {"$concat": [domain, "$cover_url"]}, "state": 1, "nick": 1
                }
            }
        ]
        cursor = client["works"].aggregate(pipeline)

        data_list = []
        for d in cursor:

            for r in report_works:
                if d["uid"] == r["works_id"]:
                    d["create_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["create_time"] / 1000))
                    break
            data_list.append(d)
        data_list = sorted(data_list, key=lambda x: x["create_time"], reverse=True)
        # 统计总数用于分页
        total_count = client["works_report"].find(
            {"type": type if type != "tj" else {"$in": ["tj", "tp"]}, "state": 1}).count()
        data["count"] = total_count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_report_works_state():
    """
    修改被举报作品状态
    """
    try:
        state = request.json.get("state")  # -1删除 1正常  3违规下架
        works_id_list = request.json.get("works_id_list")  # array
        if not state and state not in [-1, 1, 3]:
            return response(msg="Bad Request: Params 'state' is error.", code=1, status=400)
        if not works_id_list:
            return response(msg="请选择作品", code=1)
        if not isinstance(works_id_list, list):
            return response(msg="Bad Request: Params 'works_id_list' is invalid", code=1, status=400)
        if state in [-1, 3]:
            client["works"].update(
                {"uid": {"$in": works_id_list}},
                {"$set": {"state": state, "create_time": int(time.time() * 1000)}},
                multi=True
            )
            cursor = client["works"].find({"uid": {"$in": works_id_list}})
            for doc in cursor:
                if doc.get("label"):
                    for i in doc["label"]:
                        tmp = client["label"].find_one({"label": i, "state": 1})
                        if tmp and tmp["works_num"] == 1:
                            client["label"].update({"label": i}, {"$set": {"state": -1}})
                        else:
                            client["label"].update({"label": i}, {"$inc": {"works_num": -1}})
                # 作品数-1
                client["user"].update({"uid": doc.get("user_id")}, {"$inc": {"works_num": -1}})
        client["works_report"].update({"works_id": {"$in": works_id_list}}, {"$set": {"state": -1}}, multi=True)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
