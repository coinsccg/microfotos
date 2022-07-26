# -*- coding: utf-8 -*-
"""
@Time: 2021/1/3 17:24
@Auth: money
@File: material.py
"""
import time
import datetime
import base64
import random
from bson.son import SON

from initialize import init_stamp
from initialize import client
from utils.util import generate_uid
from utils.util import GenerateImage
from constant import constant


def materialUpload(data_list, user_info, user_id):
    tmp = []
    error = None
    try:
        temp_list = []
        for obj in data_list:
            uid = generate_uid(24)
            context = GenerateImage.generate_image_small(obj, "files", user_info["nick"])
            condition = {
                "uid": uid, "user_id": user_id, "pic_url": context["file_path_o"], "title": "",
                "big_pic_url": context["file_path_b"], "thumb_url": context["file_path_t"], "size": obj["size"],
                "state": 1, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000),
                "format": context["extension"].upper(), "label": [], "b_width": context["w_b"],
                "b_height": context["h_b"], "zbig_pic_url": context["file_path_z"]
            }
            temp_list.append(condition)
        cursor = client["pic_material"].insert(temp_list)
        id_list = [doc for doc in cursor]
        # 上传的素材也需要S、M、L、扩大授权规格
        pipeline = [
            {"$match": {"_id": {"$in": id_list}}},
            {
                "$project": {
                    "_id": 0, "uid": 1, "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}, "pic_url": 1,
                    "title": 1,
                    "big_pic_url": {"$concat": [constant.DOMAIN, "$big_pic_url"]}, "format": 1, "b_width": 1,
                    "b_height": 1,
                    "zbig_pic_url": {"$concat": [constant.DOMAIN, "$zbig_pic_url"]}
                }
            }
        ]
        cursor = client["pic_material"].aggregate(pipeline)

        for doc in cursor:
            # 创作S、M、L、扩大授权图
            data = {
                "file_path": doc["pic_url"],
                "file_extension": doc["format"]
            }
            context = GenerateImage.generate_image_big(data, "files")
            uid = generate_uid(24)
            spec_list = ["S", "扩大授权", "M", "L"]
            condition = []
            for i in spec_list:
                temp = {
                    "uid": uid, "user_id": user_id, "type": 0, "pic_id": doc["uid"], "format": i, "currency": "￥",
                    "price_unit": "元", "size_unit": "px", "discount": constant.DISCOUNT,
                    "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
                condition.append(temp)
            file_path_s = context["file_path_s"]
            file_path_m = context["file_path_m"]
            file_path_o = context["file_path_o"]
            # S规格
            temp_s = context["s_spec"].split("x")
            w = int(temp_s[0])
            h = int(temp_s[1])
            condition[0].update(
                {"pic_url": file_path_s if file_path_s else file_path_o, "width": w, "height": h, "state": 1}
            )

            # 扩大授权
            temp_o = context["o_spec"].split("x")
            w = int(temp_o[0])
            h = int(temp_o[1])
            condition[1].update({"pic_url": file_path_o, "width": w, "height": h, "state": 1})

            # 只有M规格存在才会有L
            if file_path_m:
                # M规格
                temp_m = context["m_spec"].split("x")
                w = int(temp_m[0])
                h = int(temp_m[1])
                condition[2].update({"pic_url": file_path_m, "width": w, "height": h, "state": 1})
                # L规格
                temp_m = context["o_spec"].split("x")
                w = int(temp_m[0])
                h = int(temp_m[1])
                condition[3].update({"pic_url": file_path_o, "width": w, "height": h, "state": 1})
            else:
                condition.pop()
                condition.pop()
            client["price"].insert(condition)
            doc["pic_url"] = constant.DOMAIN + doc["pic_url"]
            tmp.append(doc)
    except Exception as e:
        error = e
    finally:
        return tmp, error


def queryMaterialList(user_id, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "state": 1}},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "pic_url": {"$concat": [constant.DOMAIN, "$pic_url"]}, "label": 1, "title": 1,
                    "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}, "format": 1, "b_height": 1, "b_width": 1,
                    "big_pic_url": {"$concat": [constant.DOMAIN, "$big_pic_url"]},
                    "zbig_pic_url": {"$concat": [constant.DOMAIN, "$zbig_pic_url"]},
                }
            }
        ]
        cursor = client["pic_material"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryUserHistoryLabel(user_id, label_max):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "state": {"$ne": -1}}},
            {"$project": {"_id": 0, "state": 0, "user_id": 0, "create_time": 0}},
            {"$sort": SON([("update_time", -1)])},
            {"$limit": label_max}
        ]
        cursor = client["history_label"].aggregate(pipeline)
        for i in cursor:
            dataList.append(i.get("label"))
    except Exception as e:
        error = e
    finally:
        return dataList, error
