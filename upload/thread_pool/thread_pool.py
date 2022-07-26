# -*- coding: utf-8 -*-
"""
@Time: 2021/1/27 15:31
@Auth: money
@File: thread_pool.py
"""
import redis
from threading import Thread

from upload.api.video import ReadTemplateJsonData, VideoMake
from upload.weitu.images import GetImages


def runAtlas():
    r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True, password="gli123456")  # 密码认证
    index = int(r.get("index"))
    r.set("index", index + 1)
    r.close()
    demo = GetImages()
    t1 = Thread(target=demo.getImageList, args=(index,))
    t1.start()


def runVideo():
    r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True, password="gli123456")  # 密码认证
    index = int(r.get("index"))
    r.close()
    demo = VideoMake(index)
    demo.getRequestImageFromCustomToMicro()
