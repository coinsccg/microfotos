# -*- coding: utf-8 -*-
"""
@Time: 2021/3/10 16:38
@Auth: money
@File: front.py
"""
from initialize import client


def getWorks(uid):
    doc = client["works"].find_one({"uid": uid}, {"_id": 0, "pic_id": 1, "title": 1, "type": 1})
    return doc


def putBannerWorksLink(uid, inLink):
    client["banner"].update_one({"uid": uid}, {"$set": {"link": inLink}})


def getPhotoRule():
    cursor = client["photo_rule"].find({}, {"_id": 0, "type": 1, "weight": 1})
    return list(cursor)


def putPhotoRule(type, weight):
    client["photo_rule"].update_one({"type": type, "state": 1}, {"$set": {"weight": weight}})
