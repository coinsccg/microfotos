# -*- coding: utf-8 -*-
"""
@Time: 2021/3/11 13:55
@Auth: money
@File: music.py
"""
import os
from bson.son import SON

from initialize import client
from initialize import init_stamp
from constant import constant


def insertMusicInfo(title, kw, coverUrl, musicUrl):
    musicOne = client["music"].find_one({"state": {"$in": [0, 1]}}, {"_id": 0, "rank": 1}, sort=[("rank", -1)])
    if musicOne:
        rank = musicOne.get("rank") + 1
    else:
        rank = 1
    uid = os.urandom(16).hex()
    doc = {"uid": uid, "title": title, "category": kw, "cover_url": coverUrl, "music_url": musicUrl, "state": 0,
           "rank": rank}
    client["music"].insert(doc)


def updateMusicInfo(uid, title, kw, coverUrl, musicUrl):
    client["music"].update_one({"uid": uid},
                               {"$set": {"title": title, "kw": kw, "cover_url": coverUrl, "music_url": musicUrl}})


def updateMusicRank(uid, rank):
    tmp1 = client["music"].find_one({"uid": uid}, {"_id": 0, "rank": 1})
    if rank == -1:
        tmp2 = client["music"].find_one({"rank": {"$gt": tmp1.get("rank")}, "state": {"$in": [0, 1]}},
                                        {"rank": 1, "uid": 1})
        client["music"].update_one({"uid": uid}, {"$set": {"rank": tmp1.get("rank") + 1}})
        client["music"].update_one({"uid": tmp2.get("uid")}, {"$set": {"rank": tmp2.get("rank") - 1}})
    else:
        tmp2 = client["music"].find_one({"rank": {"$lt": tmp1.get("rank")}, "state": {"$in": [0, 1]}},
                                        {"rank": 1, "uid": 1})
        client["music"].update_one({"uid": uid}, {"$set": {"rank": tmp1.get("rank") - 1}})
        client["music"].update_one({"uid": tmp2.get("uid")}, {"$set": {"rank": tmp2.get("rank") + 1}})


def deleteMusic(uid):
    client["music"].update_one({"uid": uid}, {"$set": {"state": -1}})


def getMusicList(kw, category, state, pageNo, pageSize):
    pipeline = [
        {"$match": {"category": category, "state" if state != 2 else "null": state if state != 2 else None}},
        {"$match": {"title" if kw else "null": {"$regex": kw} if kw else None}},
        {"$sort": SON([("rank", 1)])},
        {"$skip": (int(pageNo) - 1) * int(pageSize)},
        {"$limit": int(pageSize)},
        {"$project": {"_id": 0, "uid": 1, "category": 1, "music_url": {"$concat": [constant.DOMAIN, "$music_url"]},
                      "rank": 1, "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]}, "state": 1, "title": 1}}
    ]
    cursor = client["music"].aggregate(pipeline)
    return list(cursor)


def getMusicCategory(kw):
    cursor = client["music_category"].find({"state": 1, "kw" if kw else "null": {"$regex": kw} if kw else None},
                                           {"_id": 0}, sort=[("rank", 1)])
    return [doc["kw"] for doc in cursor]


def updateCategoryRank(kw, rank):
    tmp1 = client["music_category"].find_one({"kw": kw}, {"_id": 0, "rank": 1})
    if rank == -1:
        tmp2 = client["music_category"].find_one({"rank": {"$gt": tmp1.get("rank")}, "state": 1}, {"rank": 1, "kw": 1})
        client["music_category"].update_one({"kw": kw}, {"$set": {"rank": tmp1.get("rank") + 1}})
        client["music_category"].update_one({"kw": tmp2.get("kw")}, {"$set": {"rank": tmp2.get("rank") - 1}})
    else:
        tmp2 = client["music_category"].find_one({"rank": {"$lt": tmp1.get("rank")}, "state": 1}, {"rank": 1, "kw": 1})
        client["music_category"].update_one({"kw": kw}, {"$set": {"rank": tmp1.get("rank") - 1}})
        client["music_category"].update_one({"kw": tmp2.get("kw")}, {"$set": {"rank": tmp2.get("rank") + 1}})


def getMusicCategory(kw):
    doc = client["music_category"].find_one({"kw": kw, "state": 1})
    return doc


def insertMusicCategory(kw):
    categoryOne = client["music_category"].find_one({"state": 1}, {"_id": 0, "rank": 1}, sort=[("rank", -1)])
    if categoryOne:
        rank = categoryOne.get("rank") + 1
    else:
        rank = 1
    doc = {"kw": kw, "rank": rank, "state": 1}
    client["music_category"].insert(doc)


def updateMusicCategory(kw):
    client["music_category"].update_one({"kw": kw, "state": 1}, {"$set": {"kw": kw}})


def deleteMusicCategory(kw):
    client["music_category"].update_one({"kw": kw, "state": 1}, {"$set": {"state": -1}})


def getTemplateList(kw, category, state, pageNo, pageSize):
    pass


def putTemplateRank(uid, rank):
    pass


def deleteTemplate(uid):
    pass


def getTemplateCategory(kw):
    cursor = client["template_category"].find({"state": 1, "kw" if kw else "null": {"$regex": kw} if kw else None},
                                              {"_id": 0}, sort=[("rank", 1)])
    return [doc["kw"] for doc in cursor]


def getTemplateCategoryOne(kw):
    doc = client["template_category"].find_one({"kw": kw, "state": 1})
    return doc


def insertTemplateCategory(kw):
    categoryOne = client["template_category"].find_one({"state": 1}, {"_id": 0, "rank": 1}, sort=[("rank", -1)])
    if categoryOne:
        rank = categoryOne.get("rank") + 1
    else:
        rank = 1
    doc = {"kw": kw, "rank": rank, "state": 1}
    client["template_category"].insert(doc)


def updateTemplateCategory(kw):
    client["template_category"].update_one({"kw": kw, "state": 1}, {"$set": {"kw": kw}})


def deleteTemplateCategory(kw):
    client["template_category"].update_one({"kw": kw, "state": 1}, {"$set": {"state": -1}})
