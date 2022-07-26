# -*- coding: utf-8 -*-
"""
@Time: 2021/1/3 17:33
@Auth: money
@File: works.py
"""
import json
import time
import datetime
from bson.son import SON

import jieba
from initialize import client
from initialize import stopword
from utils.util import generate_uid
from utils.util import genrate_file_number
from constant import constant
from filter.user import user_info
from filter.pic import pic


def queryPicWorksList(user_id, content, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "user_id": user_id, "type": "tp", "state": {"$ne": -1},
                    "title" if content != "default" else "null": \
                        {"$regex": f"{content}"} if content != "default" else None
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}], "as": "pic_item"
                }
            },
            {"$addFields": {"pic_info": {"$arrayElemAt": ["$pic_item", 0]}}},
            {
                "$addFields": {
                    "thumb_url": "$pic_info.thumb_url", "pic_url": "$pic_info.pic_url",
                    "b_height": "$pic_info.b_height", "b_width": "$pic_info.b_width",
                    "big_pic_url": "$pic_info.big_pic_url"
                }
            },
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "format": 1, "label": 1, "state": 1, "b_height": 1, "b_width": 1,
                    "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]},
                    "pic_url": {"$concat": [constant.DOMAIN, "$thumb_url"]},
                    "big_pic_url": {"$concat": [constant.DOMAIN, "$big_pic_url"]},
                    "zbig_pic_url": {"$concat": [constant.DOMAIN, "$zbig_pic_url"]},
                }
            }
        ]
        cursor = client["works"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def createPicWorks(pic_list, works_uid, user_id, label, index_str, title):
    tmp = []
    error = None
    try:
        # 制作图片作品
        pic_title = pic_list[0]["title"]
        pic_label = pic_list[0].get("label")

        # 图片素材标题更新
        client["pic_material"].update({"uid": pic_list[0].get("pic_id")}, {"$set": {"title": pic_title}})
        pic_id = [pic_list[0]["pic_id"]]  # 图片id
        pic_format = pic_list[0]["format"]
        pic_url = pic_list[0]["pic_url"].replace(constant.DOMAIN, "")
        pic_info = {
            "pic_id": pic_id[0], "title": pic_title, "label": pic_label, "pic_url": pic_url,
            "format": pic_format or 'JPG'}
        number = genrate_file_number()
        keyword = list(jieba.cut(pic_title))

        # 判断该图是否已经制作过趣图作品
        doc = client["works"].find_one({"pic_id": pic_id[0], "state": 2, "type": "tp"})
        if doc:
            raise Exception("请勿重复制作图片作品")
        temp_doc = client["price"].find_one({"pic_id": pic_id[0]})
        price_id = temp_doc["uid"]
        condition = {
            "uid": works_uid, "user_id": user_id, "pic_id": pic_id, "type": "tp", "number": number,
            "format": pic_format.upper(), "title": title, "keyword": keyword, "label": label, "state": 0,
            "recommend": -1, "is_portrait": False, "is_products": False, "pic_num": 1, "like_num": 0,
            "comment_num": 0, "tag": "商", "share_num": 0, "browse_num": 0, "sale_num": 0, "index_text": index_str,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000), "price_id": price_id,
            "pic_info": [pic_info], "browse_time": int(time.time() * 1000)
        }
        client["works"].insert(condition)

        # 更新素材表中的状态
        client["pic_material"].update(
            {"user_id": user_id, "uid": pic_id[0]}, {"$set": {"works_id": works_uid, "works_state": 0}})
        tmp = pic_id
    except Exception as e:
        error = e
    finally:
        return tmp, error


def createAltasWorks(pic_list, title, works_uid, user_id, label, index_str):
    error = None
    pic_id = []
    try:
        number = genrate_file_number()
        keyword = list(jieba.cut(title))

        pic_info = []
        tep = []
        for i in pic_list:
            temp_id = i["uid"]
            doc1 = client["works"].find_one({"uid": temp_id})
            if doc1:
                temp_id = doc1["pic_id"][0]
            if temp_id in tep:
                raise Exception("请勿选择重复的图片")

            tep.append(temp_id)

            # 图片素材标题更新
            client["pic_material"].update({"uid": temp_id}, {"$set": {"title": i["title"]}})
            i["pic_url"] = i["pic_url"].replace(constant.DOMAIN, "")
            pic_id.append(temp_id)
            pic_info.append(
                {
                    "pic_id": temp_id, "title": i["title"], "label": i["label"], "pic_url": i["pic_url"],
                    "format": i["format"] or 'JPG'
                }
            )

        condition = {
            "uid": works_uid, "user_id": user_id, "pic_id": pic_id, "type": "tj", "number": number, "title": title,
            "keyword": keyword, "label": label, "state": 0, "recommend": -1, "is_portrait": False,
            "is_products": False, "pic_num": len(pic_list), "like_num": 0, "comment_num": 0, "pic_info": pic_info,
            "share_num": 0, "browse_num": 0, "sale_num": 0, "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000), "index_text": index_str
        }
        client["works"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return pic_id, error


def worksStatistical(user_id):
    error = None
    try:
        dtime = datetime.datetime.now()
        time_str = dtime.strftime("%Y-%m-%d") + " 0{}:00:00".format(0)
        timeArray = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        today_stamp = int(time.mktime(timeArray.timetuple()) * 1000)
        doc = client["user_statistical"].find_one({"user_id": user_id, "date": today_stamp})
        if doc:
            client["user_statistical"].update(
                {"user_id": user_id, "date": today_stamp},
                {"$inc": {"works_num": 1}, "$set": {"update_time": int(time.time() * 1000)}}
            )

        else:
            condition = {
                "user_id": user_id, "date": today_stamp, "works_num": 1, "sale_num": 0, "browse_num": 0,
                "amount": float(0), "like_num": 0, "goods_num": 0, "register_num": 0, "comment_num": 0, "share_num": 0,
                "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
            client["user_statistical"].insert(condition)

    except Exception as e:
        error = e
    finally:
        return error


def labelStatistical(user_id, label):
    error = None
    try:
        for i in label:
            # 记录历史标签
            condition = {
                "user_id": user_id, "label": i, "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)}
            doc = client["history_label"].find_one({"user_id": user_id, "label": i})
            if not doc:
                client["history_label"].insert(condition)
            # 更新标签表中works_num
            doc = client["label"].find_one({"label": i, "type": "pic"})
            if not doc:
                id = generate_uid(24)
                client["label"].insert(
                    {
                        "uid": id, "priority": float(0), "type": "pic", "label": i, "works_num": 0, "state": 1,
                        "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                    }
                )
    except Exception as e:
        error = e
    finally:
        return error


def putAltasWorks(pic_list, works_id, title, label):
    error = None
    try:
        rst = list(jieba.cut(title, cut_all=False)) + label
        all_kw = [i for i in rst if i not in stopword]
        # 拼接字符串
        index_str = " ".join(all_kw)

        keyword = list(jieba.cut(title))
        pic_id = []
        pic_info = []
        tep = []
        for i in pic_list:
            temp_id = i["uid"]
            doc1 = client["works"].find_one({"uid": temp_id})
            doc2 = client["works"].find_one({"pic_id": temp_id})
            if doc1:
                temp_id = doc1["pic_id"][0]

            if temp_id in tep:
                raise Exception("请勿选择重复的图片")

            tep.append(temp_id)

            # 图片素材标题更新
            client["pic_material"].update({"uid": temp_id}, {"$set": {"title": i["title"]}})

            pic_url = i["pic_url"].replace(constant.DOMAIN, "")
            pic_id.append(temp_id)
            pic_info.append(
                {
                    "pic_id": temp_id, "title": i["title"], "label": i["label"], "pic_url": pic_url,
                    "format": i["format"] or 'JPG'
                }
            )

        client["works"].update(
            {"uid": works_id},
            {
                "$set": {
                    "pic_id": pic_id, "keyword": keyword, "pic_info": pic_info, "label": label, "state": 0,
                    "index_text": index_str, "title": title
                }
            }
        )
    except Exception as e:
        error = e
    finally:
        return error


def putAltasWorksReduceWorksNum(works_id, user_id):
    error = None
    try:
        temp2 = client["works"].find_one({"uid": works_id}, {"_id": 0, "state": 1, "user_id": 1})
        if temp2 and temp2["state"] in [2, 5]:
            temp1 = client["user"].find_one({"uid": user_id}, {"_id": 0, "works_num": 1})
            if temp1["works_num"] >= 1:
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": -1}})
            else:
                client["user"].update({"uid": user_id}, {"$set": {"works_num": 0}})
    except Exception as e:
        error = e
    finally:
        return error


def putLabelNum(works_id, label):
    error = None
    try:
        temp = client["works"].find_one({"uid": works_id})
        if temp and (temp["state"] in [2, 5]):
            for i in label:
                temp = client["label"].find_one({"label": i, "state": 2, "type": "pic"})
                if temp:
                    if temp["works_num"] == 1:
                        client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": -1, "works_num": 0}})
                    elif temp["works_num"] > 1:
                        client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})

        # 修改图片素材中works_state
        if temp["type"] == "tp":
            client["pic_material"].update({"works_id": temp["uid"]}, {"$set": {"works_state": 0}})

    except Exception as e:
        error = e
    finally:
        return error


def createVideoWorks(pic_list, title, label, user_id, me_id, tpl_obj, cover_id):
    pic_id = []
    uid = ""
    error = None
    try:
        # 去除停顿词
        rst = list(jieba.cut(title, cut_all=False)) + label
        all_kw = [i for i in rst if i not in stopword]
        # 拼接字符串
        index_str = " ".join(all_kw)

        # 制作影集作品
        uid = generate_uid(24)
        number = genrate_file_number()
        keyword = list(jieba.cut(title))

        pic_info = []
        cover_url = ""
        tep = []

        for i in pic_list:
            temp_id = i["uid"]
            doc1 = client["works"].find_one({"uid": temp_id})
            if doc1:
                temp_id = doc1["pic_id"][0]

            if temp_id in tep:
                raise Exception("请勿选择重复的图片")

            tep.append(temp_id)

            # 图片素材标题更新
            client["pic_material"].update({"uid": temp_id}, {"$set": {"title": i["title"]}})

            i["pic_url"] = i["pic_url"].replace(constant.DOMAIN, "")
            if i["uid"] == cover_id:
                coverTmpDoc = client["pic_material"].find_one({"uid": temp_id}, {"big_pic_url": 1})
                cover_url = coverTmpDoc["big_pic_url"]
            if i["uid"] == cover_id and i["type"] == "works":
                cover_id = temp_id

            pic_id.append(temp_id)

            pic_info.append(
                {
                    "pic_id": temp_id, "title": i["title"], "label": i["label"], "pic_url": i["pic_url"],
                    "format": i["format"] or 'JPG'
                }
            )

        condition = {
            "uid": uid, "user_id": user_id, "pic_id": pic_id, "type": "yj", "number": number,
            "title": title, "keyword": keyword, "label": label, "state": 0, "recommend": -1,
            "is_portrait": False, "is_products": False, "pic_num": len(pic_list), "like_num": 0,
            "comment_num": 0, "pic_info": pic_info, "share_num": 0, "browse_num": 0, "sale_num": 0,
            "create_time": int(time.time() * 1000), "me_id": me_id, "cover_id": cover_id,
            "update_time": int(time.time() * 1000), "cover_url": cover_url, "tpl_obj": tpl_obj,
            "index_text": index_str, "browse_time": int(time.time() * 1000)
        }
        client["works"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return pic_id, uid, error


def putVideoLabel(user_id, label):
    error = None
    try:
        for i in label:
            # 记录历史标签
            condition = {
                "user_id": user_id, "label": i, "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            doc = client["history_label"].find_one({"user_id": user_id, "label": i})
            if not doc:
                client["history_label"].insert(condition)

            # 更新标签
            doc = client["label"].find_one({"label": i, "type": "video"})
            if not doc:
                id = generate_uid(24)
                client["label"].insert(
                    {
                        "uid": id, "priority": float(0), "type": "pic", "label": i, "works_num": 0, "state": 1,
                        "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                    }
                )
    except Exception as e:
        error = e
    finally:
        return error


def putVideoWorks(pic_list, title, label, cover_id, works_id, me_id, tpl_obj):
    error = None
    try:
        # 去除停顿词
        rst = list(jieba.cut(title, cut_all=False)) + label
        all_kw = [i for i in rst if i not in stopword]
        # 拼接字符串
        index_str = " ".join(all_kw)

        # 制作影集作品
        keyword = list(jieba.cut(title))
        pic_id = []
        pic_info = []
        cover_url = ""
        tep = []
        for i in pic_list:
            temp_id = i["uid"]
            doc1 = client["works"].find_one({"uid": temp_id})
            if doc1:
                temp_id = doc1["pic_id"][0]

            if temp_id in tep:
                raise Exception("请勿选择重复的图片")

            tep.append(temp_id)

            # 图片素材标题更新
            client["pic_material"].update({"uid": temp_id}, {"$set": {"title": i["title"]}})
            i["pic_url"] = i["pic_url"].replace(constant.DOMAIN, "")
            if temp_id == cover_id:
                cover_url = i["pic_url"]
            pic_id.append(temp_id)
            pic_info.append(
                {
                    "pic_id": temp_id, "title": i["title"], "label": i["label"], "pic_url": i["pic_url"],
                    "format": i["format"] or 'JPG'
                }
            )
        client["works"].update(
            {"uid": works_id},
            {
                "$set": {
                    "pic_id": pic_id, "keyword": keyword, "pic_info": pic_info, "label": label, "state": 0,
                    "index_text": index_str, "cover_id": cover_id, "cover_url": cover_url, "me_id": me_id,
                    "tpl_obj": tpl_obj
                }
            }
        )
    except Exception as e:
        error = e
    finally:
        return error


def updateVideoLabel(label):
    error = None
    try:
        for i in label:
            doc = client["label"].find_one({"label": i, "type": "video"})
            if not doc:
                id = generate_uid(24)
                client["label"].insert(
                    {
                        "uid": id, "priority": float(0), "type": "video", "label": i, "works_num": 0, "state": 1,
                        "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                    }
                )
    except Exception as e:
        error = e
    finally:
        return error


def createArticleWorks(uid, title, content, user_id, desc, cover):
    error = None
    try:
        # 去除停顿词
        rst = jieba.cut(title, cut_all=False)
        all_kw = [i for i in rst if i not in stopword]
        # 拼接字符串
        index_str = " ".join(all_kw)
        if not uid:
            # 入库
            uid = generate_uid(24)
            condition = {
                "uid": uid, "user_id": user_id, "content": content, "title": title, "state": 0, "cover_url": cover,
                "type": "tw", "recommend": -1, "like_num": 0, "comment_num": 0, "share_num": 0,
                "browse_num": 0, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000),
                "pic_id": [], "desc": desc, "index_text": index_str, "browse_time": int(time.time() * 1000)
            }
            client["works"].insert(condition)
            # 统计
            # 当前day天
            dtime = datetime.datetime.now()
            time_str = dtime.strftime("%Y-%m-%d") + " 0{}:00:00".format(0)
            timeArray = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            today_stamp = int(time.mktime(timeArray.timetuple()) * 1000)
            doc = client["user_statistical"].find_one({"user_id": user_id, "date": today_stamp})
            if doc:
                client["user_statistical"].update(
                    {"user_id": user_id, "date": today_stamp},
                    {"$inc": {"works_num": 1}, "$set": {"update_time": int(time.time() * 1000)}}
                )
            else:
                condition = {
                    "user_id": user_id, "date": today_stamp, "works_num": 1, "sale_num": 0, "browse_num": 0,
                    "cover_url": cover, "amount": float(0), "like_num": 0, "goods_num": 0, "register_num": 0,
                    "comment_num": 0, "share_num": 0, "create_time": int(time.time() * 1000),
                    "update_time": int(time.time() * 1000)
                }
                client["user_statistical"].insert(condition)
        else:
            temp = client["works"].find_one({"uid": uid}, {"_id": 0, "state": 1, "user_id": 1})
            if temp["state"] in [2, 5]:
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": -1}})
            client["works"].update({"uid": uid},
                                   {"$set": {"content": content, "title": title, "state": 0, "cover_url": cover,
                                             "desc": desc}})

    except Exception as e:
        error = e
    finally:
        return uid, error


def createAltasOpionDetail(works_id):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"uid": works_id}},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}],
                    "as": "pic_temp_item"
                }
            },
            {
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "thumb_url": {"$concat": [constant.DOMAIN, "$$item.thumb_url"]},
                                "uid": "$$item.uid"
                            }
                        }
                    }
                }
            },
            {"$project": {"_id": 0, "uid": 1, "title": 1, "pic_info": 1, "pic_item": 1, "label": 1}}
        ]
        cursor = client["works"].aggregate(pipeline)

        for doc in cursor:
            temp = []
            if doc["pic_item"]:
                for i in doc["pic_item"]:
                    for j in doc["pic_title"]:
                        if i["uid"] == j["pic_id"]:
                            i["title"] = j["title"]
                            i["label"] = j["label"]
                    temp.append(i)
            doc["pic_item"] = temp
            dataList.append(doc)
    except Exception as e:
        error = e
    finally:
        return dataList, error


def createVideoOpionDetail(works_id):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"uid": works_id}},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}
                    ],
                    "as": "pic_temp_item"
                }
            },
            {
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "thumb_url": {"$concat": [constant.DOMAIN, "$$item.thumb_url"]},
                                "pic_url": {"$concat": [constant.DOMAIN, "$$item.pic_url"]},
                                "works_state": "$$item.works_state", "uid": "$$item.uid", "b_width": "$$item.b_width",
                                "b_height": "$$item.b_height", "works_id": "$$item.works_id"
                            }
                        }
                    }
                }
            },
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "pic_info": 1, "pic_item": 1, "label": 1, "me_id": 1,
                    "cover_id": 1, "tpl_obj": 1
                }
            }
        ]

        cursor = client["works"].aggregate(pipeline)

        for doc in cursor:
            temp = []
            if doc["pic_item"]:
                for i in doc["pic_item"]:
                    for j in doc["pic_info"]:
                        if i["uid"] == j["pic_id"]:
                            i["title"] = j["title"]
                            i["label"] = j["label"]
                    temp.append(i)
            doc["pic_item"] = temp
            del doc["pic_info"]
            dataList.append(doc)
    except Exception as e:
        error = e
    finally:
        return dataList, error


def recordsUserLabel(label, user_id):
    error = None
    try:
        for i in label:
            condition = {
                "user_id": user_id, "label": i, "state": 1, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            doc = client["history_label"].find_one({"user_id": user_id, "label": i})
            if not doc:
                client["history_label"].insert(condition)
            else:
                client["history_label"].update_one(
                    {"user_id": user_id, "label": i}, {"$set": {"update_time": int(time.time() * 1000)}}
                )
    except Exception as e:
        error = e
    finally:
        return error


def queryGoodsList(user_id, content, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"user_id": user_id, "state": 1}},
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
                    "title": "$works_info.title", "pic_id": "$works_info.pic_id",
                    "price_id": "$works_info.price_id", "label": "$works_info.label"
                }
            },
            {
                "$match": {
                    "$or": [
                        {"title" if content != "default" else "null": \
                             {"$regex": content} if content != "default" else None},
                        {"label" if content != "default" else "null": \
                             content if content != "default" else None}
                    ]
                }
            },
            {"$unset": ["works_item", "works_info"]},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}],
                    "as": "pic_item"
                }
            },
            {
                "$lookup": {
                    "from": "price",
                    "let": {"price_id": "$price_id", "spec": "$spec"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$uid", "$$price_id"]},
                                        {"$in": ["$format", "$$spec"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "price_temp_item"
                }
            },
            {
                "$addFields": {
                    "spec_list": {
                        "$map": {
                            "input": "$price_temp_item",
                            "as": "item",
                            "in": {"pic_url": {"$concat": [constant.DOMAIN, "$$item.pic_url"]},
                                   "format": "$$item.format"}}}
                }
            },
            {"$addFields": {"pic_info": {"$arrayElemAt": ["$pic_item", 0]}}},
            {"$addFields": {"thumb_url": "$pic_info.thumb_url"}},
            {"$unset": ["pic_item", "pic_info", "price_temp_item"]},
            {
                "$project": {
                    "_id": 0, "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]}, "title": 1, "works_id": 1,
                    "spec_list": 1, "uid": 1
                }
            }
        ]
        cursor = client["goods"].aggregate(pipeline)

        for doc in cursor:
            temp = {}
            for i in doc["spec_list"]:
                if i["format"] in temp:
                    continue
                temp[i["format"]] = i["pic_url"]
            if "扩大授权" in temp:
                doc["pic_url"] = temp["扩大授权"]
            elif "L" in temp:
                doc["pic_url"] = temp["L"]
            elif "M" in temp:
                doc["pic_url"] = temp["M"]
            else:
                doc["pic_url"] = temp["S"]
            doc.pop("spec_list")
            dataList.append(doc)
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryGoodsDetail(uid, user_id):
    data = {}
    pic_data = []
    error = None
    try:
        pipeline = [
            {"$match": {"uid": uid, "type": {"$in": ["tp", "tj"]}}},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}],
                    "as": "pic_temp_item"
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
            {
                "$lookup": {
                    "from": "follow",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}, "state": 1}}],
                    "as": "follow_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "thumb_url": {"$concat": [constant.DOMAIN, "$$item.thumb_url"]},
                                "pic_url": {"$concat": [constant.DOMAIN, "$$item.pic_url"]},
                                "keyword": "$$item.keyword", "label": "$$item.label", "uid": "$$item.uid",
                                "works_id": "$$item.works_id", "title": "$$item.title", "desc": "$$item.desc",
                                "b_width": "$$item.b_width", "b_height": "$$item.b_height"
                            }
                        }
                    },
                    "nick": "$user_info.nick", "works_num": "$user_info.works_num",
                    "fans_num": {"$size": "$follow_item"},
                    "is_follow": {
                        "$cond": {
                            "if": {"$in": [user_id, "$follow_item.fans_id"]},
                            "then": True,
                            "else": False
                        }
                    },
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["", "$user_info.head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$user_info.head_img_url"]}
                        }
                    },
                }
            },
            {"$unset": ["user_item", "user_info", "pic_temp_item", "follow_item"]},
            {"$project": {"_id": 0}}
        ]

        cursor = client["works"].aggregate(pipeline)

        for doc in cursor:
            temp = []
            if doc["pic_item"]:
                for i in doc["pic_item"]:
                    for j in doc["pic_info"]:
                        if i["uid"] == j["pic_id"]:
                            i["title"] = j["title"]
                            i["label"] = j["label"]
                    temp.append(i)
            doc["pic_item"] = temp
            pic_data.append(doc)
        if not pic_data:
            raise Exception("The picture doesn't exist")
        data["pic_data"] = pic_data[0]
    except Exception as e:
        error = e
    finally:
        return data, pic_data, error


def queryGoodsSpec(data, pic_data, user_id):
    temp2 = []
    error = None
    try:
        price_data = []
        if pic_data[0].get("price_id"):
            pipeline = [
                {"$match": {"uid": pic_data[0].get("price_id")}},
                {
                    "$lookup": {
                        "from": "goods",
                        "let": {"pic_id": "$pic_id"},
                        "pipeline": [
                            {"$match": {"user_id": user_id, "pic_id": pic_data[0].get("pic_id")[0], "state": 1}}],
                        "as": "goods_item"
                    }
                },
                {"$addFields": {"goods_info": {"$arrayElemAt": ["$goods_item", 0]}}},
                {"$addFields": {"spec": "$goods_info.spec", "pic_url": {"$concat": [constant.DOMAIN, "$pic_url"]}}},
                {
                    "$project": {
                        "_id": 0, "format": 1, "height": 1, "width": 1, "price": 1, "currency": 1,
                        "pic_url": {"$cond": {"if": {"$in": ["$format", "$spec"]}, "then": "$pic_url", "else": None}}
                    }
                }
            ]
            cursor = client["price"].aggregate(pipeline)
            price_data = [doc for doc in cursor]
        temp = data["pic_data"]["pic_item"][0]
        temp["price_data"] = price_data
        temp2 = data["pic_data"]
        temp2["pic_item"] = [temp]
    except Exception as e:
        error = e
    finally:
        return temp2, error


def queryMaterialList(user_id, content, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "user_id": user_id, "state": {"$gte": 0},
                    "title" if content != "default" else "null": {"$regex": content} if content != "default" else None
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "label": 1, "b_width": 1, "b_height": 1,
                    "thumb_url": {"$concat": [constant.DOMAIN, "$thumb_url"]},
                    "big_pic_url": {"$concat": [constant.DOMAIN, "$big_pic_url"]}, "create_time": 1
                }
            }
        ]
        cursor = client["pic_material"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def uploadMaterialPic(data_list, user_id):
    error = None
    try:
        temp_list = []
        for obj in data_list:
            uid = generate_uid(24)
            condition = {
                "uid": uid, "user_id": user_id, "pic_url": obj["file_path"], "big_pic_url": obj["file_path"],
                "thumb_url": obj["file_path"], "size": obj["size"], "state": 0, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            temp_list.append(condition)
        client["pic_material"].insert(temp_list)
    except Exception as e:
        error = e
    finally:
        return error


def queryAltasAndVideoList(user_id, state, content, page, num, type):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "type": {"$in": ["tj", "tp"]} if type == "tj" else type,
                    "state": {"$ne": -1} if state == "8" else int(state),
                    "title" if content != "default" else "null": {"$regex": content} if content != "default" else None,
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}],
                    "as": "pic_temp_item"
                }
            },
            {
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "b_width": "$$item.b_width", "b_height": "$$item.b_height"
                            }
                        }
                    }
                }
            },
            {"$addFields": {"temp_item": {"$arrayElemAt": ["$pic_item", 0]}}},
            {"$addFields": {"big_pic_url": "$temp_item.big_pic_url"}},
            {
                "$project": {
                    "_id": 0, "uid": 1, "pic_id": 1, "title": 1, "desc": 1, "big_pic_url": 1, "label": 1,
                    "state": 1, "content": 1, "create_time": 1, "pic_item": 1,
                    "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]},
                }
            }
        ]
        cursor = client["works"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryArticleList(user_id, content, state, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {
                "$match": {
                    "user_id": user_id, "type": "tw",
                    "title" if content != "default" else "null": \
                        {"$regex": content} if content != "default" else None,
                    "state": {"$ne": -1} if state == "8" else int(state)
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "uid": 1, "title": 1, "content": "$desc", "state": 1, "create_time": 1}},
        ]
        cursor = client["works"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def deleteWorks(works_id_list, user_id):
    error = None
    try:
        cursor = client["works"].find({"uid": {"$in": works_id_list}})
        for doc in cursor:
            if doc["type"] in ["tj", "tp"]:
                if doc["state"] in [2, 5]:
                    for i in doc["label"]:
                        temp = client["label"].find_one({"label": i, "state": 2, "type": "pic"})
                        if temp:
                            if temp["works_num"] == 1:
                                client["label"].update({"label": i, "type": "pic"},
                                                       {"$set": {"state": -1, "works_num": 0}})
                            elif temp["works_num"] > 1:
                                client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})
            if doc["state"] in [2, 5]:
                doc_temp = client["user"].find_one({"uid": user_id}, {"_id": 0, "works_num": 1})
                if doc_temp["works_num"] >= 1:
                    client["user"].update({"uid": user_id}, {"$inc": {"works_num": -1}})
                else:
                    client["user"].update({"uid": user_id}, {"$set": {"works_num": 0}})
            # 更改图片素材中works_state
            if doc["type"] == "tp":
                client["pic_material"].update({"works_id": doc["uid"]}, {"$set": {"works_state": -1}})

        client["works"].update({"uid": {"$in": works_id_list}}, {"$set": {"state": -1}}, multi=True)
    except Exception as e:
        error = e
    finally:
        return error


def userNewWorksRelease(user_id, uid):
    error = None
    state = 1
    result1 = False
    result2 = False
    try:
        tmp = client["works"].find_one({"uid": uid},
                                       {"label": 1, "title": 1, "pic_info": 1, "type": 1, "content": 1, "pic_id": 1})
        # 数美检测
        if tmp:
            if tmp.get("type") == "tw":
                contentList = json.loads(tmp.get("content"))["content"]
                checkContent = ""
                for i in contentList:
                    if i["text"]:
                        checkContent += i["text"]
                result2 = True
            else:
                checkContent = "".join(tmp.get("label")) + tmp.get("title") + "".join(
                    [d.get("title") for d in tmp.get("pic_info")])
                picList = tmp.get("pic_id")
                demo2 = pic.ImageFilter()
                for i in picList:
                    doc = client["pic_material"].find_one({"uid": i}, {"thumb_url": 1})
                    picURL = constant.DOMAIN + doc.get("thumb_url")

                    result2, restMsg = demo2.sendRequest("dynamic", "001", picURL)  # 图片
                    if not result2:
                        break

            demo1 = user_info.UserInfoFilter()
            result1, restMsg = demo1.sendRequest("dynamic", "001", checkContent)  # 文本
            if result1 and result2:
                state = 2
                error = releaseWorksFollowOperation(uid)
                if error:
                    raise Exception(error)
        if (not result1) or (not result2):
            client["works"].update({"user_id": user_id, "uid": uid},
                                   {"$set": {"state": 1, "update_time": int(time.time() * 1000)}})
    except Exception as e:
        error = e
    finally:
        return state, error


def queryUserPortrait(pic_id, works_id):
    data = None
    error = None
    try:
        pipeline = [
            {
                "$project": {
                    "_id": 0, "user_id": 1, "works_id": 1, "b_mobile": 1, "b_home_addr": 1,
                    "pic_url": {"$concat": [constant.DOMAIN, "$pic_url"]}, "shoot_addr": 1, "shoot_time": 1,
                    "authorizer": 1, "b_name": 1, "b_id_card": 1
                }
            }
        ]
        if pic_id:
            pipeline.insert(0, {"$match": {"pic_id": pic_id}})
        else:
            pipeline.insert(0, {"$match": {"works_id": works_id}})
        tmp = list(client["portrait"].aggregate(pipeline))
        if tmp:
            data = tmp[0]
    except Exception as e:
        error = e
    finally:
        return data, error


def queryUserProduct(pic_id, works_id):
    error = None
    data = None
    try:
        pipeline = [
            {
                "$project": {
                    "_id": 0, "uid": 1, "user_id": 1, "works_id": 1, "a_name": 1, "a_id_card": 1,
                    "a_mobile": 1, "a_home_addr": 1, "pic_url": {"$concat": [constant.DOMAIN, "$pic_url"]},
                    "a_email": 1,
                    "b_name": 1, "a_property_addr": 1, "a_property_desc": 1, "b_id_card": 1, "b_mobile": 1,
                    "b_home_addr": 1, "b_email": 1
                }
            }
        ]
        if pic_id:
            pipeline.insert(0, {"$match": {"pic_id": pic_id}})
        else:
            pipeline.insert(0, {"$match": {"works_id": works_id}})
        tmp = list(client["products"].aggregate(pipeline))
        if tmp:
            data = tmp[0]
    except Exception as e:
        error = e
    finally:
        return data, error


def putUserPortrait(pic_url, shoot_addr, shoot_time, authorizer, b_name, b_id_card, b_mobile, b_home_addr, pic_id,
                    works_id, user_id):
    error = None
    try:
        condition = {
            "pic_url": pic_url, "shoot_addr": shoot_addr, "shoot_time": shoot_time, "authorizer": authorizer,
            "b_name": b_name, "b_id_card": b_id_card, "b_mobile": b_mobile, "b_home_addr": b_home_addr,
            "pic_id": pic_id, "update_time": int(time.time()) * 1000
        }
        doc = client["portrait"].update({"works_id": works_id}, {"$set": condition})
        if doc["n"] == 0:
            uid = generate_uid(24)
            condition.update(
                {"uid": uid, "user_id": user_id, "works_id": works_id, "create_time": int(time.time()) * 1000}
            )
            client["portrait"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def putUserProduct(a_name, a_id_card, a_mobile, a_home_addr, pic_url, a_email, b_email, a_property_desc, b_name,
                   b_id_card, b_mobile, user_id, a_property_addr, pic_id, b_home_addr, works_id):
    error = None
    try:
        condition = {
            "a_name": a_name, "a_id_card": a_id_card, "a_mobile": a_mobile, "a_home_addr": a_home_addr,
            "pic_url": pic_url, "a_email": a_email, "b_email": b_email, "a_property_desc": a_property_desc,
            "b_name": b_name, "b_id_card": b_id_card, "b_mobile": b_mobile, "b_home_addr": b_home_addr,
            "a_property_addr": a_property_addr, "pic_id": pic_id, "update_time": int(time.time()) * 1000
        }
        doc = client["products"].update({"works_id": works_id}, {"$set": condition})
        if doc["n"] == 0:
            uid = generate_uid(24)
            condition.update(
                {"uid": uid, "user_id": user_id, "works_id": works_id, "create_time": int(time.time()) * 1000}
            )
            client["products"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def picSaleDetail(works_id):
    data = {}
    error = None
    type = 0
    priceItem = []
    try:
        data = client["works"].find_one({"uid": works_id},
                                        {"_id": 0, "tag": 1, "price_id": 1, "is_portrait": 1, "is_products": 1})

        price_id = data["price_id"]
        pipeline = [
            {"$match": {"uid": price_id}},
            {
                "$project": {
                    "_id": 0, "type": 1, "price": 1,
                    "format": {
                        "$cond": {
                            "if": {"$eq": ["扩大授权", "$format"]},
                            "then": {"$concat": ["$format", "售价"]},
                            "else": {"$concat": ["$format", "级分辨率售价"]}
                        }
                    },
                }
            }
        ]
        cursor = client["price"].aggregate(pipeline)
        for i in cursor:
            type = i["type"]
            del i["type"]
            priceItem.append(i)
    except Exception as e:
        error = e
    finally:
        return data, type, priceItem, error


def worksShareStatistical(works_id):
    error = None
    try:
        client["works"].update({"uid": works_id}, {"$inc": {"share_num": 1}})

        user_id = client["works"].find_one({"uid": works_id}).get("user_id")
        dtime = datetime.datetime.now()
        time_str = dtime.strftime("%Y-%m-%d") + " 0{}:00:00".format(0)
        timeArray = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        timestamp = int(time.mktime(timeArray.timetuple()) * 1000)
        doc = client["user_statistical"].update(
            {"user_id": user_id, "date": timestamp},
            {"$inc": {"share_num": 1}}
        )
        if doc["n"] == 0:
            condition = {
                "user_id": user_id, "date": timestamp, "works_num": 0, "sale_num": 0, "browse_num": 0,
                "like_num": 0, "goods_num": 0, "register_num": 0, "comment_num": 0, "share_num": 1,
                "amount": float(0), "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
            client["user_statistical"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def queryUserStaistical(user_id):
    dynamicNum = 0
    atlasNum = 0
    videoNum = 0
    articleNum = 0
    materialNum = 0
    error = None
    try:
        # 动态数
        dynamicNum = client["works"].find({"user_id": user_id, "state": {"$in": [2, 5]}}).count()
        # 图集数
        atlasNum = client["works"].find(
            {"user_id": user_id, "state": {"$ne": -1}, "type": {"$in": ["tp", "tj"]}}).count()
        # 影集数
        videoNum = client["works"].find({"user_id": user_id, "state": {"$ne": -1}, "type": "yj"}).count()
        # 图文数
        articleNum = client["works"].find({"user_id": user_id, "state": {"$ne": -1}, "type": "tw"}).count()
        # 素材数
        materialNum = client["pic_material"].find({"user_id": user_id, "state": 1}).count()
    except Exception as e:
        error = e
    finally:
        return dynamicNum, atlasNum, videoNum, articleNum, materialNum, error


def userWorksNumSub1(works_id, user_id):
    error = None
    try:
        temp2 = client["works"].find_one({"uid": works_id}, {"_id": 0, "state": 1, "user_id": 1})
        if temp2 and temp2["state"] in [2, 5]:
            temp1 = client["user"].find_one({"uid": user_id}, {"_id": 0, "works_num": 1})
            if temp1["works_num"] >= 1:
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": -1}})
            else:
                client["user"].update({"uid": user_id}, {"$set": {"works_num": 0}})

        client["works"].update({"uid": works_id}, {"$set": {"state": 7}})
    except Exception as e:
        error = e
    finally:
        return error


def updateWorksLabelStaistical(works_id):
    error = None
    try:
        doc = client["works"].find_one({"uid": works_id})
        if doc["type"] in ["tj", "tp"]:
            for i in doc["label"]:
                doc = client["label"].find_one({"label": i, "state": 1, "type": "pic"})
                if doc:
                    if doc["works_num"] == 1:
                        client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": -1, "works_num": 0}})
                    elif doc["works_num"] > 1:
                        client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})
    except Exception as e:
        error = e
    finally:
        return error


def insertComment(content, user_id, works_id, g):
    error = None
    cond = {}
    try:
        keyword = list(jieba.cut(content))
        cursor = client["bad"].find({"keyword": {"$in": keyword}, "state": 1})
        data_list = [doc for doc in cursor]
        if data_list:
            raise Exception("您输入的内容包含敏感词汇")
        uid = generate_uid(24)
        cond = {
            "uid": uid, "user_id": user_id, "works_id": works_id, "like_num": 0, "content": content, "state": 1,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }
        client["comment"].insert(cond)
        # works表评论量+1
        client["works"].update({"uid": works_id}, {"$inc": {"comment_num": 1}})
        client["works"].update({"uid": works_id}, {"$set": {"comment_time": int(time.time() * 1000)}})
        del cond["_id"]
        cond.update({"is_like": False, "nick": g.user_data["user_info"]["nick"]})
    except Exception as e:
        error = e
    finally:
        return cond, error


def addCommentStatistical(works_id):
    error = None
    try:
        today = datetime.date.today()
        today_stamp = int(time.mktime(today.timetuple()) * 1000)
        doc = client["works"].find_one({"uid": works_id})
        author_id = doc.get("user_id")
        doc = client["user_statistical"].find_one({"user_id": author_id, "date": today_stamp})
        if doc:
            client["user_statistical"].update(
                {"user_id": author_id, "date": today_stamp},
                {"$inc": {"comment_num": 1}}
            )
        else:
            condition = {
                "user_id": author_id, "date": today_stamp, "works_num": 0, "sale_num": 0, "browse_num": 0,
                "amount": float(0), "like_num": 0, "goods_num": 0, "register_num": 0,
                "comment_num": 1, "share_num": 0, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["user_statistical"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def releaseWorksFollowOperation(uid):
    error = None
    try:
        user_doc = client["works"].find_one({"uid": uid})
        user_id = user_doc["user_id"]
        title = user_doc["title"]
        client["works"].update_one(
            {"uid": uid},
            {"$set": {"state": 2, "update_time": int(time.time() * 1000)}}
        )
        # 售卖申请消息通过
        msg_uid = generate_uid(16)
        client["message"].insert(
            {
                "uid": msg_uid, "user_id": user_id, "push_people": "系统消息",
                "desc": f"您的作品《{title}》发布申请通过", "state": 1, "type": 1,
                "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
        )

        temp_doc = client["user"].find_one({"uid": user_id})
        if temp_doc["recommend"] == 1:
            client["works"].update_one({"uid": uid},
                                       {"$set": {"recommend": 1, "recomm_time": int(time.time() * 1000)}})

        if user_doc["type"] == "tp":
            client["pic_material"].update({"works_id": uid}, {"$set": {"works_state": 2}})

        if user_doc["type"] in ["tj", "tp"]:
            # 发布时统label
            for i in user_doc["label"]:
                # 更新标签表中works_num
                doc = client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": 2}})
                if doc["n"] == 0:
                    uid = generate_uid(16)
                    client["label"].insert(
                        {
                            "uid": uid, "priority": 0.0, "type": "pic", "label": i,
                            "works_num": 1, "state": 2, "create_time": int(time.time() * 1000),
                            "update_time": int(time.time() * 1000)
                        }
                    )
                else:
                    count = client["works"]. \
                        find({"label": i, "type": {"$in": ["tp", "tj"]}, "state": {"$in": [2, 5]}}).count()
                    client["label"].update({"label": i, "type": "pic"}, {"$set": {"works_num": count + 1}})
        # 如果作者被推荐，那么作品加入摄影推荐列表
        photo_doc = client["show_search_module"].find_one({"type": "pic"})
        user_temp_doc = client["user"].find_one({"uid": user_id})
        if photo_doc["state"] == 1 and user_temp_doc["group"] == "auth" and (user_doc["type"] in ["tp", "tj"]):
            client["works"].update({"uid": uid},
                                   {"$set": {"photo_recomm": 1, "recomm_photo_time": int(time.time() * 1000)}})

        # 作品数+1
        client["user"].update({"uid": user_id}, {"$inc": {"works_num": 1}})
    except Exception as e:
        error = e
    finally:
        return error


def spiderCreateArticleWorks(title, content, desc, cover, author_name):
    error = None
    uid = ""
    user_id = ""
    try:
        # 去除停顿词
        rst = jieba.cut(title, cut_all=False)
        all_kw = [i for i in rst if i not in stopword]
        # 拼接字符串
        index_str = " ".join(all_kw)

        # 判断是否为第一次上传
        tmpDoc = client["user"].find_one({"author_name": author_name}, {"uid": 1})

        if not tmpDoc:
            startTime = 1611849600000
            endTime = 1611936000000
            pipeline = [
                {"$match": {"mobile": {"$regex": "144"},
                            "$and": [{"create_time": {"$gte": startTime}}, {"create_time": {"$lte": endTime}}]}},
                {"$sample": {"size": 1}},
                {"$project": {"uid": 1}}
            ]

            userDoc = client["user"].aggregate(pipeline)

            userDoc = [doc for doc in userDoc]
            print(userDoc)
            user_id = userDoc[0]["uid"]

            # 记录作者
            client["user"].update_one({"uid": user_id}, {"$set": {"author_name": author_name}})
        else:
            user_id = tmpDoc["uid"]

        cover = cover.replace(constant.DOMAIN, "")

        # 入库
        uid = generate_uid(24)
        condition = {
            "uid": uid, "user_id": user_id, "content": content, "title": title.replace("\n", "", -1), "state": 0,
            "cover_url": cover,
            "type": "tw", "recommend": -1, "like_num": 0, "comment_num": 0, "share_num": 0,
            "browse_num": 0, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000),
            "pic_id": [], "desc": desc.lstrip("\n") or "", "index_text": index_str,
            "browse_time": int(time.time() * 1000)
        }
        client["works"].insert(condition)

        # 统计
        # 当前day天
        dtime = datetime.datetime.now()
        time_str = dtime.strftime("%Y-%m-%d") + " 0{}:00:00".format(0)
        timeArray = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        today_stamp = int(time.mktime(timeArray.timetuple()) * 1000)
        doc = client["user_statistical"].find_one({"user_id": user_id, "date": today_stamp})
        if doc:
            client["user_statistical"].update(
                {"user_id": user_id, "date": today_stamp},
                {"$inc": {"works_num": 1}, "$set": {"update_time": int(time.time() * 1000)}}
            )
        else:
            condition = {
                "user_id": user_id, "date": today_stamp, "works_num": 1, "sale_num": 0, "browse_num": 0,
                "cover_url": cover, "amount": float(0), "like_num": 0, "goods_num": 0, "register_num": 0,
                "comment_num": 0, "share_num": 0, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["user_statistical"].insert(condition)

    except Exception as e:
        error = e
    finally:
        return uid, user_id, error


def getUserMobile(uid):
    user = client["user"].find_one({"uid": uid, "state": {"$ne": -1}}, {"_id": 0, "uid": 1, "mobile": 1})
    return user


def getMusicList():
    cursor = client["music"].find_one({"state": 1}, {"_id": 0}, sort=[("rank", 1)])
    musicList = []
    for m in cursor:
        musicUrl = m.get("music_url")
        coverUrl = m.get("cover_url")
        m["music_url"] = constant.DOMAIN + musicUrl
        m["cover_url"] = constant.DOMAIN + coverUrl
        musicList.append(m)
    return musicList
