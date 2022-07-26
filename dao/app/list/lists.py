# -*- coding: utf-8 -*-
"""
@Time: 2021/1/4 13:33
@Auth: money
@File: lists.py
"""
import time
import datetime
from bson.son import SON

from initialize import client
from constant import constant


def incBrowseRecords(user_id, works_id):
    error = None
    try:

        doc = client["works"].find_one({"uid": works_id})
        author_id = doc.get("user_id")

        # 记录
        condition = {
            "user_id": user_id, "works_id": works_id, "type": doc["type"], "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        client["browse_records"].insert(condition)

        # 浏览量+1
        client["works"].update({"uid": works_id}, {"$inc": {"browse_num": 1}})
        client["works"].update({"uid": works_id}, {"$set": {"browse_time": int(time.time() * 1000)}})

        # 凌晨时间戳
        today = datetime.date.today()
        today_stamp = int(time.mktime(today.timetuple()) * 1000)
        doc = client["user_statistical"].find_one({"user_id": author_id, "date": today_stamp})
        if doc:
            client["user_statistical"].update(
                {"user_id": author_id, "date": today_stamp}, {"$inc": {"browse_num": 1}}
            )
        else:
            condition = {
                "user_id": author_id, "date": today_stamp, "works_num": 0, "sale_num": 0,
                "browse_num": 1, "amount": float(0), "like_num": 0, "goods_num": 0, "register_num": 0,
                "comment_num": 0, "share_num": 0, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["user_statistical"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def queryAltasDetail(works_id, user_id):
    pic_obj = {}
    error = None
    try:
        # 图片详情信息
        pipeline = [
            {"$match": {"uid": works_id, "type": {"$in": ["tp", "tj"]}}},
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
            {
                "$lookup": {
                    "from": "like_records",
                    "let": {"uid": "$uid"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$works_id", "$$uid"]},
                                "type": "zp", "user_id": user_id
                            }
                        }
                    ],
                    "as": "like_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]}
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
                                "title": "$$item.title", "uid": "$$item.uid", "label": "$$item.label",
                                "keyword": "$$item.keyword", "works_state": "$$item.works_state",
                                "b_width": "$$item.b_width", "b_height": "$$item.b_height",
                                "works_id": "$$item.works_id", "format": "$$item.format", "desc": "$$item.desc"
                            }
                        }
                    },
                    "works_num": "$user_info.works_num", "nick": "$user_info.nick",
                    "label": {"$slice": ["$label", 30]},
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["", "$user_info.head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$user_info.head_img_url"]}
                        }
                    },
                    "is_follow": {
                        "$cond": {
                            "if": {"$in": [user_id, "$follow_item.fans_id"]},
                            "then": True,
                            "else": False
                        }
                    },
                    "is_like": {
                        "$cond": {
                            "if": {"$eq": ["$like_info.state", 1]},
                            "then": True,
                            "else": False
                        }
                    },
                }
            },
            {"$unset": ["user_item", "user_info", "pic_temp_item", "follow_item", "like_item", "like_info"]},
            {"$project": {"_id": 0}}
        ]
        pic_data = list(client["works"].aggregate(pipeline))
        if not pic_data:
            raise Exception("works_id invalid")
        pic_obj = pic_data[0]
        temp = []
        if pic_obj["pic_item"]:
            for i in pic_obj["pic_item"]:
                for j in pic_obj["pic_info"]:
                    if i["uid"] == j["pic_id"]:
                        i["title"] = j["title"]
                        i["label"] = j["label"]
                # 筛选与此作品对应的价格信息，并满足state=1
                tempp_doc = client["works"].find_one({"pic_id": i["uid"], "type": "tp", "state": 5})
                price_data = []
                # 价格信息存在并且state=5才能购买
                if tempp_doc and tempp_doc.get("price_id") and tempp_doc.get("state") == 5:

                    temp_cursor = client["price"].find(
                        {"uid": tempp_doc["price_id"], "state": 1}, {"_id": 0}
                    )
                    tempp = None
                    for c in temp_cursor:
                        # 判断规格是否购买
                        gg = client["goods"].find_one(
                            {"user_id": user_id, "pic_id": c["pic_id"], "spec": c["format"], "state": 1}
                        )
                        c["is_buy"] = False
                        if gg:
                            c["is_buy"] = True

                        if c["format"] != "扩大授权":
                            price_data.append(c)
                        else:
                            tempp = c
                    price_data = sorted(price_data, key=lambda x: x["format"], reverse=True)
                    price_data.append(tempp)
                    i["tag"] = tempp_doc["tag"]
                    i["is_portrait"] = tempp_doc["is_portrait"]
                    i["is_products"] = tempp_doc["is_products"]
                i["price_data"] = price_data
                temp.append(i)
        # pic_obj["pic_item"] = sorted(temp, key=lambda x: x["uid"])
        pic_obj["pic_item"] = temp
        del pic_obj["pic_info"]
        temp_obj = {}
        n = 0
        for i in pic_obj["pic_id"]:
            temp_obj.update({i: n})
            n += 1
        # 将列表按照指定值排序
        o = sorted(temp, key=lambda x: temp_obj[x["uid"]])
        pic_obj["pic_item"] = o
    except Exception as e:
        error = e
    finally:
        return pic_obj, error


def queryVideoDetail(uid, user_id):
    temp = {}
    error = None
    try:
        pipeline = [
            {"$match": {"uid": uid}},
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
                    "from": "video_material",
                    "let": {"video_id": "$video_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$video_id"]}}}],
                    "as": "video_item"
                }
            },
            {
                "$lookup": {
                    "from": "audio_material",
                    "let": {"audio_id": "$audio_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$audio_id"]}}}],
                    "as": "audio_item"
                }
            },
            {
                "$lookup": {
                    "from": "like_records",
                    "let": {"uid": "$uid"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$works_id", "$$uid"]},
                                "type": "zp", "user_id": user_id
                            }
                        }
                    ],
                    "as": "like_item"
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
                                "uid": "$$item.uid", "label": "$$item.label", "title": "$$item.title",
                                "desc": "$$item.desc", "keyword": "$$item.keyword", "b_height": "$$item.b_height",
                                "works_id": "$$item.works_id", "works_state": "$$item.works_state",
                                "b_width": "$$item.b_width"
                            }
                        }
                    },
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "video_info": {"$arrayElemAt": ["$video_item", 0]},
                    "audio_info": {"$arrayElemAt": ["$audio_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]}
                }
            },
            {
                "$addFields": {
                    "nick": "$user_info.nick", "works_num": "$user_info.works_num",
                    "audio_url": "$audio_info.audio_url", "video_url": "$video_info.video_url",
                    "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]},
                    "is_follow": {
                        "$cond": {
                            "if": {"$eq": ["$user_info.uid", user_id]},
                            "then": True,
                            "else": False
                        }
                    },
                    "is_like": {
                        "$cond": {
                            "if": {"$eq": ["$like_info.state", 1]},
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
                    }
                }
            },
            {
                "$unset": [
                    "pic_temp_item", "user_item", "user_info", "video_item", "audio_item", "video_info",
                    "audio_info", "like_item", "like_info"
                ]
            },
            {"$project": {"_id": 0, "tpl_obj": 0}}
        ]
        cursor = client["works"].aggregate(pipeline)
        data = [doc for doc in cursor]
        if not data:
            raise Exception("works_id is not exists")
        temp = data[0]
        for i in temp["pic_item"]:
            if i["uid"] == temp["cover_id"]:
                temp["b_width"] = i["b_width"]
                temp["b_height"] = i["b_height"]
    except Exception as e:
        error = e
    finally:
        return temp, error


def queryArticleDetail(uid, user_id):
    temp = {}
    error = None
    try:
        pipeline = [
            {"$match": {"uid": uid}},
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
            {
                "$lookup": {
                    "from": "like_records",
                    "let": {"uid": "$uid"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$works_id", "$$uid"]}, "type": "zp", "user_id": user_id}}
                    ],
                    "as": "like_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]}
                }
            },
            {
                "$addFields": {
                    "nick": "$user_info.nick", "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]},
                    "works_num": "$user_info.works_num",
                    "is_follow": {
                        "$cond": {
                            "if": {"$in": [user_id, "$follow_item.fans_id"]},
                            "then": True,
                            "else": False
                        }
                    },
                    "is_like": {
                        "$cond": {
                            "if": {"$eq": ["$like_info.state", 1]},
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
                    }
                }
            },
            {"$unset": ["user_item", "user_info", "follow_item", "like_item", "like_info"]},
            {"$project": {"_id": 0}}
        ]
        cursor = client["works"].aggregate(pipeline)
        data = [doc for doc in cursor]
        if not data:
            raise Exception("uid is not exists")
        temp = data[0]
    except Exception as e:
        error = e
    finally:
        return temp, error


def queryAuthorFansNum(user_id):
    fansNum = 0
    error = None
    try:
        fansNum = client["follow"].find({"user_id": user_id, "state": 1}).count()
    except Exception as e:
        error = e
    finally:
        return fansNum, error


def query2CommentList(works_id, user_id):
    error = None
    dataList = []
    try:

        # 查询评论
        pipeline = [
            {"$match": {"works_id": works_id, "state": {"$ne": -1}}},
            {"$sort": SON([("like_num", -1), ("create_time", -1)])},
            {"$limit": 10},
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
                    "from": "comment_report",
                    "let": {"comment_id": "$uid"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$comment_id", "$$comment_id"]}, "state": 1}}],
                    "as": "report_item"
                }
            },
            {
                "$lookup": {
                    "from": "like_records", "let": {"comment_id": "$uid"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$comment_id", "$$comment_id"]},
                                        {"$eq": [user_id, "$user_id"]}, {"$eq": [1, "$state"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "like_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]},
                }
            },
            {
                "$addFields": {
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$user_info.head_img_url", ""]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$user_info.head_img_url"]}
                        }
                    },
                    "nick": "$user_info.nick",
                    "is_like": {
                        "$cond": {
                            "if": {"$eq": [1, "$like_info.state"]},
                            "then": True,
                            "else": False
                        }
                    },
                    "is_report": {
                        "$cond": {
                            "if": {"$in": [user_id, "$report_item.user_id"]},
                            "then": True,
                            "else": False
                        }
                    }
                }
            },
            {"$unset": ["user_item", "user_info", "like_item", "like_info", "report_item"]},
            {"$sort": SON([("like_num", -1), ("create_time", -1)])},
            {"$project": {"_id": 0}}
        ]
        dataList = list(client["comment"].aggregate(pipeline))

    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryWorksList(condition, sort, user_id, skip, num, is_rank=False, rule_dict=None):
    dataList = []
    error = None
    try:

        # 过审模式判断
        audit = client["audit"].find_one({}, {"_id": 0, "state": 1})
        if audit["state"] == 1:
            condition["$match"].update({"type": {"$ne": "yj"}})

        pipeline = [
            condition,
            sort,
            skip,
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
            {
                "$lookup": {
                    "from": "like_records",
                    "let": {"uid": "$uid"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$works_id", "$$uid"]},
                                "type": "zp", "user_id": user_id
                            }
                        }
                    ],
                    "as": "like_item"
                }
            },
            {
                "$lookup": {
                    "from": "browse_records",
                    "let": {"works_id": "$uid", "user_id": "$user_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$works_id", "$$works_id"]},
                                        {"$eq": ["$user_id", user_id]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "browse_item"
                }
            },
            {
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "thumb_url": {"$concat": [constant.DOMAIN, "$$item.thumb_url"]},
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "zbig_pic_url": {"$concat": [constant.DOMAIN, "$$item.zbig_pic_url"]},
                                "keyword": "$$item.keyword", "label": "$$item.label", "uid": "$$item.uid",
                                "desc": "$$item.desc", "title": "$$item.title", "works_id": "$$item.works_id",
                                "b_height": "$$item.b_height", "b_width": "$$item.b_width"
                            }
                        }
                    },
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]}
                }
            },
            {
                "$addFields": {
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$user_info.head_img_url", ""]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$user_info.head_img_url"]}
                        }
                    },
                    "nick": "$user_info.nick", "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]},
                    "works_num": "$user_info.works_num",
                    "label": {"$slice": ["$label", 5]},
                    "count": {
                        "$cond": {
                            "if": {"$in": [user_id, "$browse_item.user_id"]},
                            "then": 1,
                            "else": 0
                        }
                    },
                    "is_like": {
                        "$cond": {
                            "if": {"$eq": ["$like_info.state", 1]},
                            "then": True,
                            "else": False
                        }
                    },
                    "is_follow": {
                        "$cond": {
                            "if": {"$in": [user_id, "$follow_item.fans_id"]},
                            "then": True,
                            "else": False
                        }
                    }
                }
            },
            {
                "$unset": [
                    "pic_temp_item", "user_item", "user_info",
                    "like_info", "browse_item", "follow_item", "like_item"
                ]
            },
            sort,
            {"$project": {"_id": 0, "pic_info": 0, "tpl_obj": 0, "browse_time": 0, "temp_rank": 0}},
        ]
        if is_rank:
            pipeline.insert(
                1,
                {"$addFields": {
                    "temp_rank": {"$add": [
                        {"$multiply": [{"$ln": {"$add": ["$browse_num", 1]}}, 0.1, rule_dict["browse"]]},
                        {"$multiply": [{"$ln": {"$add": ["$like_num", 1]}}, 0.1, rule_dict["like"]]},
                        {"$multiply": [{"$ln": {"$add": ["$comment_num", 1]}}, 0.1, rule_dict["comment"]]},
                        {"$multiply": [
                            {"$ln": {
                                "$add": [{"$divide": [{"$subtract": ["$update_time", constant.BENCH]}, 86400000]},
                                         1]}},
                            0.1, rule_dict["time"]]
                        }
                    ]}
                }}
            )
            pipeline[-2] = {"$sort": SON([("temp_rank", -1)])}
        cursor = client["works"].aggregate(pipeline)

        for doc in cursor:
            doc["top"] = False
            # 查询评论
            comment_list, error = query2CommentList(doc["uid"], user_id)
            if error:
                raise Exception(error)
            doc["comment_list"] = comment_list
            # 查找粉丝数
            count = client["follow"].find({"user_id": doc["user_id"], "state": 1}).count()
            doc["fans_num"] = count
            # picItem图片排序
            temp_obj = {}
            n = 0
            if doc.get("pic_id"):
                for i in doc["pic_id"]:
                    temp_obj.update({i: n})
                    n += 1
                # 将列表按照指定值排序
                o = sorted(doc["pic_item"], key=lambda x: temp_obj[x["uid"]])
                doc["pic_item"] = o

            # 由于之前的作品数是通过works_num字段+-1统计，后来数据一致性难以保证，将作品数量统计
            userId = doc.get("user_id")
            worksNum = client["works"].find({"user_id": userId, "state": {"$in": [2, 5]}}).count()
            doc["works_num"] = worksNum

            dataList.append(doc)

    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryAuthorList(user_id, limit):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"uid": {"$ne": user_id}, "state": 1, "type": "user", "works_num": {"$gte": 1}}},
            {
                "$lookup": {
                    "from": "follow",
                    "let": {"user_id": "$uid"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}}},
                        {"$count": "count"}
                    ],
                    "as": "follow_item"
                }
            },
            {"$addFields": {"follow_info": {"$arrayElemAt": ["$follow_item", 0]}}},
            {"$addFields": {"fans_num": "$follow_info.count"}},
            {"$sample": {"size": limit}},
            {
                "$project": {
                    "_id": 0, "user_id": "$uid", "nick": 1, "works_num": 1, "fans_num": 1,
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$head_img_url", ""]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                        }
                    }
                }
            }
        ]
        temp = pipeline
        cursor = client["user"].aggregate(pipeline)
        author_list = []
        for doc in cursor:
            if "fans_num" not in doc:
                doc["fans_num"] = 0
            if doc["user_id"] != user_id:
                author_list.append(doc)

        temp_list = []
        if len(author_list) < 10:
            temp[0] = {"$match": {"uid": {"$ne": user_id}, "state": 1, "type": "user", "works_num": {"$lte": 0}}}
            temp[4] = {"$sample": {"size": limit - len(author_list)}}
            cursor = client["user"].aggregate(temp)
            for doc in cursor:
                if "fans_num" not in doc:
                    doc["fans_num"] = 0
                if doc["user_id"] != user_id:
                    temp_list.append(doc)
        dataList = author_list + temp_list
    except Exception as e:
        error = e
    finally:
        return dataList, error


def querySearchAuthorList(user_id, keyword):
    dataList = []
    error = None
    try:
        cursor = client["follow"].find({"fans_id": user_id, "state": 1})
        follow_author_id = [doc["user_id"] for doc in cursor]
        pipeline = [
            {"$match": {"nick": {"$regex": f"{keyword}"}}},
            {
                "$lookup": {
                    "from": "follow",
                    "let": {"user_id": "$uid"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}, "state": 1}},
                        {"$count": "count"}
                    ],
                    "as": "follow_item"
                }
            },
            {"$addFields": {"follow_info": {"$arrayElemAt": ["$follow_item", 0]}}},
            {"$addFields": {"fans_num": "$follow_info.count"}},
            {
                "$project": {
                    "_id": 0, "user_id": "$uid", "nick": 1, "works_num": 1, "fans_num": 1,
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["", "$head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                        }
                    },
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        for doc in cursor:
            if doc["user_id"] in follow_author_id:
                doc["is_follow"] = True
            else:
                doc["is_follow"] = False
            if "fans_num" not in doc:
                doc["fans_num"] = 0
            dataList.append(doc)
    except Exception as e:
        error = e
    finally:
        return dataList, error


def likeWorksStatistical(works_id, temp):
    error = None
    try:
        today = datetime.date.today()
        today_stamp = int(time.mktime(today.timetuple()) * 1000)
        doc = client["works"].find_one({"uid": works_id})
        author_id = doc.get("user_id")
        doc = client["user_statistical"].find_one({"user_id": author_id, "date": today_stamp})

        if doc:
            if (temp and temp["state"] == 0) or (not temp):
                client["user_statistical"].update(
                    {"user_id": author_id, "date": today_stamp}, {"$inc": {"like_num": 1}}
                )
        else:
            condition = {
                "user_id": author_id, "date": today_stamp, "works_num": 0, "sale_num": 0, "browse_num": 0,
                "amount": float(0), "like_num": 1, "goods_num": 0, "register_num": 0,
                "comment_num": 0, "share_num": 0, "create_time": int(time.time() * 1000),
                "update_time": int(time.time() * 1000)
            }
            client["user_statistical"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def likeWorksRecords(user_id, works_id):
    error = None
    try:
        doc = client["like_records"].find_one({"user_id": user_id, "works_id": works_id, "type": "zp"})
        if doc:
            if doc["state"] == 1:
                client["like_records"].update(
                    {"user_id": user_id, "works_id": works_id, "type": "zp"},
                    {"$set": {"state": 0, "update_time": int(time.time() * 1000)}}
                )
            else:
                client["like_records"].update(
                    {"user_id": user_id, "works_id": works_id, "type": "zp"},
                    {"$set": {"state": 1, "update_time": int(time.time() * 1000)}}
                )
        else:
            condition = {
                "user_id": user_id, "works_id": works_id, "type": "zp", "state": 1,
                "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
            client["like_records"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def likeWorksChangeNum(user_id, works_id):
    temp = {}
    error = None
    try:
        temp = client["like_records"].find_one({"user_id": user_id, "works_id": works_id, "type": "zp"})

        if temp and temp["state"] == 1:
            # 点赞量-1
            client["works"].update({"uid": works_id}, {"$inc": {"like_num": -1}})
        else:
            # 点赞量+1
            client["works"].update({"uid": works_id}, {"$inc": {"like_num": 1}})
        client["works"].update({"uid": works_id}, {"$set": {"like_time": int(time.time() * 1000)}})
    except Exception as e:
        error = e
    finally:
        return temp, error


def queryCommentList(user_id, works_id, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"works_id": works_id, "state": {"$ne": -1}}},
            {"$sort": SON([("like_num", -1), ("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num) + 10},
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
                    "from": "comment_report",
                    "let": {"comment_id": "$uid"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$comment_id", "$$comment_id"]}, "state": 1}}],
                    "as": "report_item"
                }
            },
            {
                "$lookup": {
                    "from": "like_records",
                    "let": {"comment_id": "$uid"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$comment_id", "$$comment_id"]},
                                        {"$eq": [user_id, "$user_id"]},
                                        {"$eq": [1, "$state"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "like_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]}
                }
            },
            {
                "$addFields": {
                    "is_like": {"$cond": {"if": {"$eq": [1, "$like_info.state"]}, "then": True, "else": False}},
                    "nick": "$user_info.nick", "like_num": {"$size": "$like_item"},
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["", "$user_info.head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$user_info.head_img_url"]}
                        }
                    },
                    "is_report": {
                        "$cond": {
                            "if": {"$in": [user_id, "$report_item.user_id"]},
                            "then": True,
                            "else": False
                        }
                    }
                }
            },
            {"$unset": ["user_item", "user_info", "like_item", "like_info", "report_item"]},
            {"$sort": SON([("like_num", -1), ("create_time", -1)])},
            {"$project": {"_id": 0}}
        ]
        cursor = client["comment"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def insertLikeComment(user_id, works_id, comment_id):
    n = 0
    error = None
    try:
        doc = client["like_records"].find_one(
            {"user_id": user_id, "works_id": works_id, "comment_id": comment_id, "type": "pl"}
        )
        n = 1
        if doc:
            condition = {"user_id": user_id, "works_id": works_id, "comment_id": comment_id, "type": "pl"}
            if doc["state"] == 1:
                client["like_records"].update(
                    condition,
                    {"$set": {"state": 0, "update_time": int(time.time() * 1000)}}
                )
                n = -1
            else:
                client["like_records"].update(
                    condition,
                    {"$set": {"state": 1, "update_time": int(time.time() * 1000)}}
                )
                n = 1
        else:
            condition = {
                "user_id": user_id, "works_id": works_id, "comment_id": comment_id, "type": "pl", "state": 1,
                "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
            client["like_records"].insert(condition)
            n = 1
    except Exception as e:
        error = e
    finally:
        return n, error


def likeCommentNum(comment_id, n):
    error = None
    try:
        client["comment"].update({"uid": comment_id}, {"$inc": {"like_num": n}})
    except Exception as e:
        error = e
    finally:
        return error


def appVersion():
    error = None
    data = {}
    try:
        doc = client["version"].find_one(
            {"state": 1, "is_latest": True},
            {"_id": 0, "version_str": 1, "version_num": 1, "size": 1, "desc": 1, "link": 1, "option": 1, "tip_way": 1},
            sort=[("create_time", -1)])
        if doc:
            doc["link"] = constant.DOMAIN + doc["link"]
            data = doc
    except Exception as e:
        error = e
    finally:
        return data, error


def getAuditStatus():
    doc = client["audit"].find_one({}, {"_id": 0, "state": 1})
    return doc["state"]


def putAuditStatus(state):
    client["audit"].update_one({}, {"$set": {"state": state}})
