# -*- coding: utf-8 -*-
"""
@Time: 2021/1/4 14:51
@Auth: money
@File: user_info.py
"""

import requests
import json

from filter.conf import conf


class UserInfoFilter(object):
    """用户信息过滤器"""

    def __init__(self):
        self.payload = dict()
        self.payload["accessKey"] = conf.accessKey
        self.payload["type"] = "SOCIAL"
        self.payload["appId"] = "default"
        self.payload["eventId"] = "default"
        self.payload["data"] = {}

    def _riskType(self, code):
        riskType = "正常"
        if code == 100:
            riskType = "涉政"
        elif code == 200:
            riskType = "色情"
        elif code == 210:
            riskType = "辱骂"
        elif code == 300:
            riskType = "广告"
        elif code == 400:
            riskType = "灌水"
        elif code == 500:
            riskType = "无意义"
        elif code == 510:
            riskType = "不良场景"
        elif code == 600:
            riskType = "违禁"
        elif code == 700:
            riskType = "其他"
        elif code == 720:
            riskType = "黑账号"
        elif code == 730:
            riskType = "黑IP"
        elif code == 800:
            riskType = "高危账号"
        elif code == 900:
            riskType = "自定义"
        if code == 0:
            return True, None
        else:
            return False, riskType

    def sendRequest(self, channel, tokenId, text):
        """
        param channel: 场景， 如:昵称、签名
        param tokenId: 用户账号唯一标识，如uid
        param text: 需要检测的内容
        """
        tmpChannel = conf.textChannel[channel]
        self.payload["data"]["channel"] = tmpChannel
        self.payload["data"]["text"] = str(text)
        self.payload["data"]["tokenId"] = tokenId
        headers = {"Content-Type": "application/json"}

        i = 1
        while True:
            # 服务超时，请求5次
            if i >= 6:
                return False, "Shumei service timeout"
            res = requests.post(conf.textURL, json=self.payload, headers=headers, timeout=1).json()
            print(res)
            if res.get("status") == 501:
                i += 1
                continue
            elif res.get("code") == 1100:
                break
            else:
                return True, "Internal Server Error"

        code = json.loads(res.get("detail")).get("riskType")
        riskRest, riskType = self._riskType(code)
        if riskRest:
            return True, None
        else:
            return False, riskType


if __name__ == '__main__':
    demo = UserInfoFilter()
    demo.sendRequest("nick", "767902639f923ebf92163a2f99e3f589", "你好")