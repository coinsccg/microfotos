# -*- coding: utf-8 -*-
"""
@Time: 2021/1/3 16:38
@Auth: money
@File: user.py
"""
import time
from bson.son import SON

from initialize import client
from dao.app.list.lists import query2CommentList
from constant import constant
from dao.app.order import orders


def queryLikeHistoryList(user_id, page, num, type):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},

            {
                "$lookup": {
                    "from": "comment",
                    "let": {"comment_id": "$comment_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$comment_id"]}}}],
                    "as": "comment_item"
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
            {"$addFields": {"comment_info": {"$arrayElemAt": ["$comment_item", 0]}}},
            {
                "$addFields": {
                    "comment_like_num": "$comment_info.like_num", "content": "$comment_info.content",
                    "comment_user_id": "$comment_info.user_id"
                }
            },
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": {
                        "$cond": {"if": {"$eq": ["$type", "zp"]}, "then": "$user_id", "else": "$comment_user_id"}}},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
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
                    "author_id": "$works_info.user_id", "nick": "$user_info.nick",
                    "is_like": {"$cond": {"if": {"$eq": [1, "$state"]}, "then": True, "else": False}},
                    "title": "$works_info.title", "works_like_num": "$works_info.like_num",
                    "works_type": "$works_info.type",
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["", "$user_info.head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$user_info.head_img_url"]}
                        }
                    },
                }
            },
            {
                "$lookup": {
                    "from": "user",
                    "let": {"author_id": "$author_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$author_id"]}}}],
                    "as": "author_item"
                }
            },
            {"$addFields": {"author_info": {"$arrayElemAt": ["$author_item", 0]}}},
            {
                "$addFields": {
                    "author_nick": "$author_info.nick",
                    "author_head_img": {
                        "$cond": {
                            "if": {"$eq": ["", "$author_info.head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$author_info.head_img_url"]}
                        }
                    },
                }
            },
            {
                "$unset": [
                    "works_item", "comment_item",
                    "author_item", "author_info", "user_info", "user_item"
                ]
            },
            {
                "$project": {
                    "_id": 0, "is_like": 1, "comment_like_num": 1, "title": 1, "comment_id": 1, "type": 1,
                    "uid": "$comment_id", "create_time": "$update_time", "content": 1, "works_id": 1,
                    "works_like_num": 1, "works_type": 1,
                    "nick": {
                        "$cond": {
                            "if": {"$eq": ["$type", "zp"]},
                            "then": "$author_nick" if type == "1" else "$nick",
                            "else": "$nick" if type == "1" else "$author_nick"
                        }
                    },
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$type", "zp"]},
                            "then": "$author_head_img" if type == "1" else "$head_img_url",
                            "else": "$head_img_url" if type == "1" else "$author_head_img"
                        }
                    }
                }
            },

            {"$sort": SON([("create_time", -1)])}
        ]
        if type == "1":
            pipeline.insert(0, {"$match": {"user_id": user_id, "state": 1}}, )
        else:
            cursor = client["works"].find({"user_id": user_id, "state": {"$in": [2, 5]}})
            works_id_list = [doc["uid"] for doc in cursor if doc]

            cursor1 = client["comment"].find({"user_id": user_id, "state": 1}, {"uid": 1})
            commentIdList = [doc["uid"] for doc in cursor1 if doc]
            pipeline.insert(0, {
                "$match": {"$or": [{"works_id": {"$in": works_id_list}}, {"comment_id": {"$in": commentIdList}}],
                           "state": 1}})
        cursor = client["like_records"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryCommentHistoryList(user_id, page, num, type):
    dataList = []
    error = None
    try:
        pipeline = [
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
                    "from": "like_records",
                    "let": {"uid": "$uid"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$comment_id", "$$uid"]}}}],
                    "as": "like_item"
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
                    "like_info": {"$arrayElemAt": ["$like_item", 0]},
                    "works_info": {"$arrayElemAt": ["$works_item", 0]}
                }
            },
            {
                "$addFields": {
                    "nick": "$user_info.nick",
                    "is_like": {
                        "$cond": {
                            "if": {
                                "$and": [
                                    {"$eq": [user_id, "$like_info.user_id"]},
                                    {"$eq": [1, "$like_info.state"]}]},
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
                    "title": "$works_info.title", "works_type": "$works_info.type"
                }
            },
            {"$unset": ["user_info", "user_item", "works_item"]},
            {
                "$project": {
                    "_id": 0, "nick": 1, "is_like": 1, "like_num": 1, "head_img_url": 1, "works_type": 1,
                    "works_id": 1, "create_time": 1, "content": 1, "title": 1, "uid": 1
                }
            }
        ]
        if type == "1":
            pipeline.insert(0, {"$match": {"user_id": user_id, "state": 1}})
        else:
            cursor = client["works"].find({"user_id": user_id, "state": {"$in": [2, 5]}})
            works_id_list = [doc["uid"] for doc in cursor]
            pipeline.insert(0, {"$match": {"works_id": {"$in": works_id_list}, "state": 1}})
        cursor = client["comment"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryUserInfo(author_id, user_id):
    userInfo = {}
    error = None
    try:
        pipeline = [
            {"$match": {"uid": author_id}},
            {
                "$project": {
                    "_id": 0, "uid": 1, "nick": 1, "sex": 1, "sign": 1,
                    "works_num": 1, "label": 1, "login_time": 1, "group": 1,
                    "update_time": 1, "mobile": 1, "auth": 1, "create_time": 1,
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["$head_img_url", ""]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                        }
                    },
                    "background_url":
                        {
                            "$cond": {
                                "if": {"$eq": ["$background_url", ""]},
                                "then": "",
                                "else": {"$concat": [constant.DOMAIN, "$background_url"]}
                            }
                        },
                }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        if not data_list:
            raise Exception("user_id is not exists")
        userInfo = data_list[0]

        # 查询是否关注
        userInfo["is_follow"] = False
        tmp = client["follow"].find_one({"user_id": author_id, "fans_id": user_id, "state": 1})
        if tmp:
            userInfo["is_follow"] = True

    except Exception as e:
        error = e
    finally:
        return userInfo, error


def queryUserDataStatistics(author_id, user_id):
    orderCount = 0
    dynamicCount = 0
    commentNum = 0
    likeNum = 0
    followNum = 0
    fansNum = 0
    msgNum = 0
    unpaidNum = 0
    error = None
    try:
        # 更新订单状态 支付超时更新状态
        error = orders.updateOrderState(user_id)
        if error:
            raise Exception(error)
        # 待付款订单数
        orderCount = client["order"].find({"user_id": user_id, "state": 0}).count()
        # 关注用户的作品动态数
        pipeline = [
            {"$match": {"fans_id": user_id, "state": 1}},
            {"$project": {"_id": 0, "user_id": 1, "last_look_time": 1, "create_time": 1}}
        ]
        cursor = client["follow"].aggregate(pipeline)
        user_list = []
        n = 0
        m = 0
        last_look_time = int(time.time() * 1000)
        for doc in cursor:
            user_list.append(doc["user_id"])
            if n == 0:
                last_look_time = doc["last_look_time"]
                n += 1
            if doc["last_look_time"] == doc["create_time"]:
                m += 1
        condition = {"user_id": {"$in": user_list}, "create_time": {"$gte": last_look_time}}
        dynamicCount = client["works"].find(condition).count()
        # 评论数
        worksList = client["works"].find({"user_id": author_id if author_id else user_id, "state": {"$in": [2, 5]}},
                                         {"_id": 0, "uid": 1})
        worksIdList = [doc["uid"] for doc in worksList]
        commentNum = client["comment"].find({"works_id": {"$in": worksIdList}, "state": 1}).count()
        # 点赞数
        cursor1 = client["comment"].find({"user_id": user_id, "state": 1}, {"uid": 1})
        commentIdList = [doc["uid"] for doc in cursor1 if doc]
        likeNum = client["like_records"].find(
            {"$or": [{"works_id": {"$in": worksIdList}}, {"comment_id": {"$in": commentIdList}}], "state": 1}).count()
        # 粉丝数
        fansNum = client["follow"].find({"user_id": author_id if author_id else user_id, "state": 1}).count()
        # 关注数
        followNum = client["follow"].find({"fans_id": author_id if author_id else user_id, "state": 1}).count()
        # 消息数
        msgNum = client["message"].find({"user_id": author_id if author_id else user_id, "state": 1}).count()
        # 未支付的订单数
        payPipeline = [
            {"$match": {"user_id": user_id, "state": 1}},
            {"$group": {"_id": "$order"}},
            {"$project": {"_id": 1}}
        ]
        cursorPay = client["order"].aggregate(payPipeline)
        unpaidNum = len(list(cursorPay))
        if m >= 1:
            dynamicCount = 1
    except Exception as e:
        error = e
    finally:
        return orderCount, dynamicCount, commentNum, likeNum, fansNum, followNum, msgNum, unpaidNum, error


def queryUserFollowDynimac(user_id):
    data = {}
    error = None
    try:
        pipeline = [
            {"$match": {"fans_id": user_id, "state": 1}},
            {"$project": {"_id": 0, "user_id": 1, "last_look_time": 1}}
        ]
        cursor = client["follow"].aggregate(pipeline)
        user_list = []
        n = 0
        last_look_time = int(time.time() * 1000)
        for doc in cursor:
            user_list.append(doc["user_id"])
            if n == 0:
                last_look_time = doc["last_look_time"]
                n += 1
        pipeline = [
            {"$match": {"user_id": {"$in": user_list}, "state": 2}},
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
                    "let": {"works_id": "$works_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$works_id"]}}}],
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
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "label": "$$item.label",
                                "thumb_url": {"$concat": [constant.DOMAIN, "$$item.thumb_url"]},
                                "title": "$$item.title",
                                "desc": "$$item.desc", "keyword": "$$item.keyword", "uid": "$$item.uid",
                                "works_id": "$$item.works_id", "b_width": "$$item.b_width",
                                "b_height": "$$item.b_height"
                            }
                        }
                    },
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "browse_info": {"$arrayElemAt": ["$browse_item", 0]},
                    "video_info": {"$arrayElemAt": ["$video_item", 0]},
                    "audio_info": {"$arrayElemAt": ["$audio_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]}
                }
            },
            {
                "$addFields": {
                    "nick": "$user_info.nick",
                    "works_num": "$user_info.works_num", "video_url": "$video_info.video_url",
                    "audio_url": "$audio_info.audio_url", "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]},
                    "count": {"$cond": {"if": {"$in": [user_id, "$browse_item.user_id"]}, "then": 1, "else": 0}},
                    "is_like": {"$cond": {"if": {"$eq": [user_id, "$like_info.user_id"]}, "then": True, "else": False}},
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
                    "pic_temp_item", "user_item", "user_info", "browse_info", "browse_item", "video_item", "audio_item",
                    "video_info", "audio_info", "like_item", "like_info"
                ]
            },
            {"$sort": SON([("create_time", -1)])},
            {"$project": {"_id": 0}}
        ]
        cursor = client["works"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        count = client["works"].find(
            {"user_id": {"$in": user_list}, "create_time": {"$gte": last_look_time}, "state": {"$in": [2, 5]}}
        ).count()
        data["count"] = count
        data["works_list"] = data_list
        client["follow"].update(
            {"user_id": {"$in": user_list}, "fans_id": user_id},
            {"$set": {"last_look_time": int(time.time() * 1000)}}
        )
    except Exception as e:
        error = e
    finally:
        return data, error


def queryUserOwnFollowList(user_id, search_kw):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"fans_id": user_id, "state": 1}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$replaceRoot": {"$newRoot": {"$mergeObjects": [{"$arrayElemAt": ["$user_item", 0]}]}}},
            {"$match": {"nick": {"$regex": search_kw}}},
            {
                "$project": {
                    "_id": 0, "user_id": 1, "nick": 1, "works_num": 1,
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["", "$head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                        }
                    }
                }
            }
        ]
        cursor = client["follow"].aggregate(pipeline)
        dataList = [doc for doc in cursor]
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryFollowList(user_id, author_id, search_kw, page, num):
    dataList = []
    error = None
    try:
        pipeline = [
            {"$match": {"fans_id": author_id, "state": 1}},
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
                    "from": "follow",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}, "state": 1}},
                        {"$count": "count"}
                    ],
                    "as": "follow_item"
                }
            },
            # {"$replaceRoot": {"$newRoot": {"$mergeObjects": [{"$arrayElemAt": ["$user_item", 0]}]}}},
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "follow_info": {"$arrayElemAt": ["$follow_item", 0]}
                }
            },
            {
                "$addFields": {
                    "head_img_url": "$user_info.head_img_url", "nick": "$user_info.nick",
                    "works_num": "$user_info.works_num", "fans_num": "$follow_info.count",
                    "login_time": "$user_info.login_time"
                }
            },
            {"$unset": ["user_item", "user_info", "follow_info", "follow_item"]},
            {
                "$project": {
                    "_id": 0, "user_id": 1, "nick": 1, "login_time": 1,
                    "works_num": 1, "fans_num": {"$ifNull": ["$fans_num", 0]},
                    "head_img_url": {
                        "$cond": {
                            "if": {"$eq": ["", "$head_img_url"]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                        }
                    }
                }
            }
        ]
        if search_kw != "default" and search_kw is not None:
            pipeline.insert(7, {"$match": {"nick": {"$regex": f"{search_kw}"}}})
        cursor = client["follow"].aggregate(pipeline)

        # 当前用户的关注
        temp = client["follow"].find({"fans_id": user_id, "state": 1})
        user_follow_list = [doc["user_id"] for doc in temp]
        for doc in cursor:
            if doc["user_id"] in user_follow_list:
                doc["is_follow"] = True
            else:
                doc["is_follow"] = False
            dataList.append(doc)
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryFansList(user_id, author_id, page, num):
    dataList = []
    error = None
    try:
        # 查询数据
        pipeline = [
            {"$match": {"user_id": author_id, "state": 1}},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"fans_id": "$fans_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$fans_id"]}}}],
                    "as": "user_item"
                }
            },
            {
                "$lookup": {
                    "from": "follow",
                    "let": {"fans_id": "$fans_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$user_id", "$$fans_id"]}, "state": 1}},
                        {"$count": "count"}
                    ],
                    "as": "follow_item"
                }
            },
            # {"$replaceRoot": {"$newRoot": {"$mergeObjects": [{"$arrayElemAt": ["$user_item", 0]}]}}},
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "follow_info": {"$arrayElemAt": ["$follow_item", 0]}
                }
            },
            {
                "$addFields": {
                    "head_img_url": "$user_info.head_img_url", "nick": "$user_info.nick",
                    "works_num": "$user_info.works_num", "fans_num": "$follow_info.count",
                    "login_time": "$user_info.login_time"
                }
            },
            {"$unset": ["user_item", "user_info", "follow_info", "follow_item"]},
            {
                "$project": {
                    "_id": 0, "user_id": "$fans_id", "nick": 1, "login_time": 1, "works_num": 1,
                    "fans_num": {"$ifNull": ["$fans_num", 0]},
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
        cursor = client["follow"].aggregate(pipeline)

        # 当前用户的关注
        temp = client["follow"].find({"fans_id": user_id, "state": 1})
        user_follow_list = [doc["user_id"] for doc in temp]
        for doc in cursor:
            if doc["user_id"] in user_follow_list:
                doc["is_follow"] = True
            else:
                doc["is_follow"] = False
            dataList.append(doc)
    except Exception as e:
        error = e
    finally:
        return dataList, error


def queryUserWorksList(author_id, user_id, page, num):
    worksList = []
    error = None
    try:

        condition = {"$match": {"user_id": author_id, "state": {"$in": [2, 5]}}}
        # 过审模式判断
        audit = client["audit"].find_one({}, {"_id": 0, "state": 1})
        if audit["state"] == 1:
            condition["$match"].update({"type": {"$ne": "yj"}})

        # 用户作品
        pipeline = [
            condition,
            {"$sort": SON([("update_time", -1)])},
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
                "$lookup": {
                    "from": "video_material",
                    "let": {"video_id": "$video_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$video_id"]}}}],
                    "as": "video_item"
                }
            },
            {
                "$lookup": {
                    "from": "like_records",
                    "let": {"uid": "$uid"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$works_id", "$$uid"]}, "type": "zp", "state": 1}}],
                    "as": "like_item"
                }
            },
            {
                "$lookup": {
                    "from": "browse_records",
                    "let": {"works_id": "$u id", "user_id": "$user_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$works_id", "$$works_id"]},
                                        {"$eq": ["$user_id", author_id]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "browse_item"
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
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "big_pic_url": {"$concat": [constant.DOMAIN, "$$item.big_pic_url"]},
                                "zbig_pic_url": {"$concat": [constant.DOMAIN, "$$item.zbig_pic_url"]},
                                "thumb_url": {"$concat": [constant.DOMAIN, "$$item.thumb_url"]},
                                "title": "$$item.title",
                                "desc": "$$item.desc", "keyword": "$$item.keyword", "label": "$$item.label",
                                "uid": "$$item.uid", "works_id": "$$item.works_id", "b_width": "$$item.b_width",
                                "b_height": "$$item.b_height"
                            }
                        }
                    },
                    "browse_info": {"$arrayElemAt": ["$browse_item", 0]},
                    "video_info": {"$arrayElemAt": ["$video_item", 0]},
                    "like_info": {"$arrayElemAt": ["$like_item", 0]},
                    "user_info": {"$arrayElemAt": ["$user_item", 0]}
                }
            },
            {
                "$addFields": {
                    "video_url": "$video_info.video_url", "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]},
                    "count": {"$cond": {"if": {"$in": [author_id, "$browse_item.user_id"]}, "then": 1, "else": 0}},
                    "nick": "$user_info.nick", "works_num": "$user_info.works_num",
                    "is_follow": {
                        "$cond": {
                            "if": {"$in": [user_id, "$follow_item.fans_id"]},
                            "then": True,
                            "else": False
                        }
                    },
                    "is_like": {
                        "$cond": {
                            "if": {"$eq": [user_id, "$like_info.user_id"]},
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
                    "pic_temp_item", "browse_info", "video_item", "video_info", "like_item", "like_info",
                    "browse_item", "user_item", "user_info", "follow_item"
                ]
            },
            {"$sort": SON([("update_time", -1)])},
            {"$project": {"_id": 0}}
        ]
        cursor = client["works"].aggregate(pipeline)
        for doc in cursor:
            # 查询评论
            comment_list, error = query2CommentList(doc["uid"], user_id)
            if error:
                raise Exception(error)
            doc["comment_list"] = comment_list
            # 粉丝数
            count = client["follow"].find({"user_id": doc["user_id"], "state": 1}).count()
            doc["fans_num"] = count
            # 由于之前的作品数是通过works_num字段+-1统计，后来数据一致性难以保证，将作品数量统计
            userId = doc.get("user_id")
            worksNum = client["works"].find({"user_id": userId, "state": {"$in": [2, 5]}}).count()
            doc["works_num"] = worksNum
            worksList.append(doc)

    except Exception as e:
        error = e
    finally:
        return worksList, error


def authCamerman(name, id_card, id_card_a_url, id_card_b_url, temp_list, addr, user_id):
    error = None
    try:
        condition = {
            "id_card_name": name, "id_card": id_card, "id_card_a_url": id_card_a_url,
            "id_card_b_url": id_card_b_url, "repre_works": temp_list, "auth": 1, "id_card_addr": addr,
            "update_time": int(time.time() * 1000)
        }
        client["user"].update({"uid": user_id}, {"$set": condition})
    except Exception as e:
        error = e
    finally:
        return error


def balanceRelevant(user_id, yesterday_stamp):
    balance = 0
    fees = 0
    amount = 0
    lock = 0
    error = None
    try:
        # 余额
        doc = client["user"].find_one({"uid": user_id, "state": 1}, {"_id": 0, "balance": 1})
        if doc:
            balance = doc.get("balance")

        # 昨日收入
        doc = client["user_statistical"].find_one(
            {"user_id": user_id, "date": yesterday_stamp}, {"_id": 0, "amount": 1}
        )
        if doc:
            amount = doc.get("amount")

        # 手续费
        tmp = list(client["bank"].find({"state": 1}))
        if tmp:
            fees = tmp[0]["fees"]

        # 提现金额
        temp = client["withdrawal_records"].find({"user_id": user_id, "state": 1})
        for doc in temp:
            lock += doc["amount"]

    except Exception as e:
        error = e
    finally:
        return balance, amount, fees, lock, error


def withdrawlBankList():
    error = None
    dataList = []
    try:
        cursor = client["bank"].find({"state": 1}, {"_id": 0, "uid": 1, "name": 1})
        dataList = [doc for doc in cursor]
        if not dataList:
            raise Exception("Internal Server Error: Lack of data in database.")
    except Exception as e:
        error = e
    finally:
        return dataList, error


def getForbiddenUser(user_id):
    data = {}
    error = None
    try:
        data = client["forbidden"].find_one({"user_id": user_id, "state": 1})
    except Exception as e:
        error = e
    finally:
        return data, error


def getUser(uid):
    user = {}
    error = None
    try:
        pipeline = [
            {"$match": {"uid": uid}},
            {"$project": {
                "_id": 0, "uid": 1, "nick": 1, "sex": 1, "sign": 1, "mobile": 1, "auth": 1, "state": 1,
                "works_num": 1, "label": 1, "login_time": 1, "group": 1, "create_time": 1, "update_time": 1,
                "head_img_url": {
                    "$cond": {
                        "if": {"$eq": ["$head_img_url", ""]},
                        "then": "",
                        "else": {"$concat": [constant.DOMAIN, "$head_img_url"]}
                    }
                },
                "background_url":
                    {
                        "$cond": {
                            "if": {"$eq": ["$background_url", ""]},
                            "then": "",
                            "else": {"$concat": [constant.DOMAIN, "$background_url"]}
                        }
                    },
            }
            }
        ]
        cursor = client["user"].aggregate(pipeline)
        user = [doc for doc in cursor][0]
    except Exception as e:
        error = e
    finally:
        return user, error


def updateUserPasswordAndMobile(userId, mobile, password):
    error = None
    try:
        client["user"].update_one({"uid": userId},
                                  {"$set": {"mobile": mobile, "account": mobile, "password": password}})
    except Exception as e:
        error = e
    finally:
        return error


def updateUserPassword(userId, password):
    error = None
    try:
        client["user"].update_one({"uid": userId}, {"$set": {"password": password}})
    except Exception as e:
        error = e
    finally:
        return error


def getUserMobile(mobile):
    error = None
    tmp = False
    try:
        doc = client["user"].find_one({"mobile": mobile, "state": {"$ne": -1}}, {"_id": 1})
        if doc:
            tmp = True
    except Exception as e:
        error = e
    finally:
        return tmp, error


def getUserInfo(mobile):
    doc = client["user"].find_one({"mobile": mobile, "state": {"$ne": -1}}, {"_id": 0})
    return doc
