# -*- coding: utf-8 -*-
"""
@Time: 2021/1/4 14:53
@Auth: money
@File: pic.py
"""
import base64
import json

import requests

from filter.conf import conf


class ImageFilter(object):
    """图片过滤器"""

    def __init__(self):
        self.payload = dict()
        self.payload["accessKey"] = conf.accessKey
        self.payload["type"] = "POLITICS_PORN_AD_BEHAVIOR"
        self.payload["appId"] = "default"
        self.payload["data"] = {}

    def _riskType(self, code):
        riskType = "正常"
        if code == 100:
            riskType = "涉政"
        elif code == 200:
            riskType = "色情"
        elif code == 210:
            riskType = "性感"
        elif code == 300:
            riskType = "广告"
        elif code == 310:
            riskType = "二维码"
        elif code == 320:
            riskType = "水印"
        elif code == 400:
            riskType = "暴恐"
        elif code == 500:
            riskType = "违规"
        elif code == 510:
            riskType = "不良场景"
        elif code == 700:
            riskType = "黑名单"
        elif code == 710:
            riskType = "白名单"
        elif code == 800:
            riskType = "高危账号"
        elif code == 900:
            riskType = "自定义"
        if code == 0:
            return True, None
        else:
            return False, riskType

    def sendRequest(self, channel, tokenId, picPath):
        """
        param channel: 场景 如：动态、头像
        param tokenId: 用户账号唯一标识，如uid
        param picPath: 要检测图片路径
        """
        tmpChannel = conf.imgChannel[channel]

        self.payload["data"]["channel"] = tmpChannel
        # base64.b64encode(content).decode("utf-8")
        self.payload["data"]["img"] = picPath
        self.payload["data"]["tokenId"] = tokenId

        headers = {"Content-Type": "application/json"}

        i = 1
        while True:
            # 服务超时，请求5次
            if i >= 6:
                return False, "Shumei service timeout"
            res = requests.post(conf.imageURL, json=self.payload, headers=headers, timeout=10).json()
            if res.get("status") == 501:
                i += 1
                continue
            elif res.get("code") == 1100:
                break
            else:
                return True, "Internal Server Error"
        code = res.get("detail").get("riskType")
        riskRest, riskType = self._riskType(code)

        if riskRest:
            return True, None
        else:
            return False, riskType


if __name__ == '__main__':
    demo = ImageFilter()
    demo.sendRequest("dynamic", "001", "http://m.microfotos.cn/6796405e7764e6c01344eebc05e0c496/2020/12/0f38e751cd45cbe53a10273221c16024_t.jpg")
