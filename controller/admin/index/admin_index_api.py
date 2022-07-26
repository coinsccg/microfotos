# -*- coding: utf-8 -*-
"""
@Time: 2020/06/30 16:27:08
@File: admin_index_api
@Auth: money
"""
import time
import datetime
from bson.son import SON
from flask import request
from middleware.auth import response
from utils.util import generate_timestamp
from initialize import log
from initialize import client
from initialize import init_stamp


def get_top_statistics():
    """首页顶部统计接口"""
    data = {}
    try:
        # today时间戳
        today = datetime.date.today()
        today_stamp = int(time.mktime(today.timetuple()) * 1000)
        # 查询数据
        pipeline = [
            {
                "$addFields": {
                    "today_amount": {
                        "$cond": {
                            "if": {"$eq": ["$date", today_stamp]},
                            "then": "$amount",
                            "else": 0
                        }
                    },
                    "today_works": {
                        "$cond": {
                            "if": {"$eq": ["$date", today_stamp]},
                            "then": "$works_num",
                            "else": 0
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": None, "register_num": {"$sum": "$register_num"},
                    "goods_num": {"$sum": "$goods_num"}, "amount_num": {"$sum": "$today_amount"},
                    "inc_works_num": {"$sum": "$today_works"}
                }
            },
            {
                "$project": {
                    "_id": 0, "register_num": 1, "amount_num": {"$round": ["$amount_num", 2]},
                    "inc_works_num": 1
                }
            },
        ]
        cursor = client["user_statistical"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        works_num = client["works"].find({"state": {"$in": [2, 5]}}).count()
        release_num = client["works"].find({"state": {"$in": [1, 4]}}).count()
        user_num = client["user"].find({"auth": 1, "state": 1, "type": {"$in": ["org", "user"]}}).count()
        register_num = client["user"].find({"state": 1, "type": {"$in": ["org", "user"]}}).count()
        data["works_num"] = works_num
        data["user_num"] = user_num
        data.update(data_list[0] if data_list else {})
        data["register_num"] = register_num
        data["release_num"] = release_num
        # 违规下架的作品超过24小时未编辑则自动删除
        _, before_timestamp = generate_timestamp(days=1)
        cursor = client["works"].find({"state": 3}, {"_id": 0, "create_time": 1, "uid": 1})

        for doc in cursor:
            if doc["create_time"] < before_timestamp:
                client["works"].update({"uid": doc["uid"]}, {"$set": {"state": -1}})

        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def get_data_statistics():
    """数据统计趋势"""
    data = {}
    try:
        # 获参数
        day = request.args.get("day")
        if not day:
            return response(msg="Bad Request: Miss params: 'day'.", code=1, status=400)
        # 当前day天
        dtime = datetime.datetime.now()
        time_str = dtime.strftime("%Y-%m-%d") + " 0{}:00:00".format(0)
        timeArray = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        today_stamp = int(time.mktime(timeArray.timetuple()) * 1000)
        last_stamp = int(time.mktime((timeArray - datetime.timedelta(days=int(day) - 1)).timetuple()) * 1000)
        pipeline = [
            {"$match": {"$and": [{"date": {"$gte": last_stamp}}, {"date": {"$lte": today_stamp}}]}},
            {"$group": {"_id": "$date", "amount": {"$sum": "$amount"}}},
            {
                "$project": {
                    "_id": 0, "amount": 1,
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$add": [init_stamp, "$_id"]}}}
                }
            },
            {"$sort": SON([("date", 1)])}
        ]
        cursor = client["user_statistical"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        data["data_list"] = data_list if data_list else []
        # 当前总计
        pipeline = [
            {"$match": {"$and": [{"date": {"$gte": last_stamp}}, {"date": {"$lte": today_stamp}}]}},
            {"$group": {"_id": None, "total_amount": {"$sum": "$amount"}, "total_sale": {"$sum": "$sale_num"}}},
            {"$project": {"_id": 0, "total_amount": {"$round": ["$total_amount", 2]}, "total_sale": 1}}
        ]
        cursor = client["user_statistical"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        if not data_list:
            raise Exception("No data in the database")
        today_total = data_list[0]
        # 过去总计
        last_stamp = int(time.mktime((timeArray - datetime.timedelta(days=int(day))).timetuple()) * 1000)
        last_befor_stamp = int(time.mktime((timeArray - datetime.timedelta(days=int(day) * 2 - 1)).timetuple()) * 1000)
        pipeline = [
            {"$match": {"$and": [{"date": {"$gte": last_befor_stamp}}, {"date": {"$lte": last_stamp}}]}},
            {"$group": {"_id": None, "total_amount": {"$sum": "$amount"}, "total_sale": {"$sum": "$sale_num"}}},
            {"$project": {"_id": 0, "total_amount": 1, "total_sale": 1}}
        ]
        cursor = client["user_statistical"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        if not data_list:
            obj = {
                "total_amount": 0,
                "total_sale": 0
            }
            data_list.append(obj)
        befor_total = data_list[0]
        amount_delta = 0 if today_total.get("total_amount") == 0 and befor_total.get("total_amount") == 0 else \
            (today_total.get("total_amount") - befor_total.get("total_amount")) / befor_total.get(
                "total_amount") if befor_total.get("total_amount") != 0 else 1
        sale_delta = 0 if today_total.get("total_sale") == 0 and befor_total.get("total_sale") == 0 else \
            (today_total.get("total_sale") - befor_total.get("total_sale")) / befor_total.get(
                "total_sale") if befor_total.get("total_sale") != 0 else 1
        amount_delta = "%.2f" % amount_delta
        sale_delta = "%.2f" % sale_delta
        today_total["amount_delta"] = float(amount_delta)
        today_total["sale_delta"] = float(sale_delta)
        data["compare_data"] = today_total
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
