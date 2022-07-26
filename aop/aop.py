# -*- coding: utf-8 -*-
"""
@Time: 2021/1/25 14:48
@Auth: money
@File: aop.py
"""
import time
import functools
from flask import g
from flask import request

from middleware.auth import response
from dao.app.user import user


def userForbiddenVerify(f):
    @functools.wraps(f)
    def wrappers(*args, **kwargs):
        url = request.url
        if url.endswith("works/comment") or url.endswith("user/works/batch") or url.endswith(
                "user/works/apply") or url.endswith("user/works/pic/sell"):
            userId = g.user_data["user_id"]
            doc, error = user.getForbiddenUser(userId)
            if doc is not None:
                if doc.get("expire_time") > int(time.time() * 1000):
                    return response(msg="您当前处于禁言状态，禁止发布或售卖", code=1)

        return f(*args, **kwargs)

    return wrappers
