# -*- coding: utf-8 -*-
"""
@Time: 2021/1/4 14:52
@Auth: money
@File: conf.py
"""

# 数美应用access_key
accessKey = 'OFcKEAdnvlHrvNz7M64N'
# 文本请求URL
textURL = 'http://api-text-bj.fengkongcloud.com/v2/saas/anti_fraud/text'
# 图片请求URL
imageURL = 'http://api-img-bj.fengkongcloud.com/v2/saas/anti_fraud/img'

# 文本场景
textChannel = {
    "nick": "WTNC",
    "dynamic": "WTWBDT",
    "comment": "WTPL",
    "sign": "WTGXQM"
}

# 图片场景
imgChannel = {
    "img": "WTTX",
    "dynamic": "WTTPDT",
    "bgc": "WTZYBJ"
}