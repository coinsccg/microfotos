# -*- coding: utf-8 -*-
"""
@Time: 2021/2/2 9:47
@Auth: money
@File: app.py
"""


class User(object):
    """
    用户模型
    """
    uid: str
    nick: str
    sex: str
    age: int
    mobile: str
    password: str
    head_img_url: str
    background_url: str
    state: int
    account: str
    auth: int
    type: str
    balance: float
    works_num: int
    group: str
    label: list
    create_time: int
    update_time: int
    login_time: int
    recommend: int
    sign: str
    token: str
    recommend: int
    oauth: dict


class UserStatistical(object):
    """
    用户数据统计模型
    """
    user_id: str
    date: int
    works_num: int
    sale_num: int
    browse_num: int
    like_num: int
    goods_num: int
    register_num: int
    comment_num: int
    share_num: int
    amount: float
    create_time: int
    update_time: int
