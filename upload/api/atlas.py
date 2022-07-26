# -*- coding: utf-8 -*-
"""
@Time: 2021/1/26 10:06
@Auth: money
@File: atlas.py
"""
import os

import requests

from upload.api.user import CreateUser
from upload.config import config


class AtlasWorks(object):
    """
    图集作品上传
    """

    def __init__(self):
        self.domain = config.DOMAIN  # 域名
        self.url1 = self.domain + "/api/v1/user/local/upload"  # 图片
        self.url2 = self.domain + "/api/v1/user/creation/atlas"  # 图集创作
        self.url3 = self.domain + "/api/v1/user/works/batch"  # 发布审核
        self.url4 = self.domain + "/api/v1/user/works/apply"  # 售卖申请
        self.url5 = self.domain + "/api/v1/admin/works/audit"  # 作品审核
        self.url6 = self.domain + "/api/v1/admin/login"  # 管理员登录

    def uploadImage(self, imageURL: str, imageId: int, token: str):
        """
        上传图片
        """
        res1 = requests.get(imageURL)
        content = res1.content
        headers = {
            "token": token
        }
        res2 = requests.post(self.url1, files=[("pic_list[]", (f"{imageId}.jpg", content, "image/jpg"))],
                             headers=headers)
        error = None
        picBigURL = ""
        picUID = ""
        if res2.status_code == 200:
            if res2.json().get("code") == 0:
                data = res2.json().get("data")[0]

                picBigURL = data["big_pic_url"]
                picUID = data["uid"]
            else:
                error = "image invalid: " + res2.json().get("msg")
        else:
            error = res2.text
        return picBigURL, picUID, error

    def insertAtlasRelease(self, token: str, worksId: str):
        """
        发布审核
        """
        headers = {
            "token": token
        }
        data = {
            "uid": worksId
        }
        res = requests.post(self.url3, json=data, headers=headers)
        error = None
        if res.status_code != 200:
            error = res.text
        return error

    def insertAtlasSell(self, token: str, worksId: str):
        """售卖申请"""
        headers = {
            "token": token
        }
        data = {
            "works_id": worksId,
            "tag": "商",
            "code": 0,
            "price_item": []
        }
        res = requests.post(self.url4, json=data, headers=headers)
        error = None
        if res.status_code != 200:
            error = res.text
        return error

    def updateAtlasWorksAudit(self, worksId: str):
        """
        作品审核
        """
        # 管理员登录
        token, error = self.adminUserLogin()
        if error is not None:
            return error
        headers = {
            "Content-Type": "application/json",
            "token": token,
            "module_id": "003",
            "permission_id": "049"
        }
        data = {
            "works_id": [worksId],
            "node": "",
            "state": 2
        }
        res = requests.put(self.url5, json=data, headers=headers)
        error = None
        if res.status_code != 200:
            error = res.text
        return error

    def adminUserLogin(self):
        """
        管理员登录
        """
        data = {
            "account": config.ADMIN_USERNAME,
            "password": config.ADMIN_PASSWORD
        }
        res = requests.post(self.url6, json=data)
        error = None
        token = ""
        if res.status_code != 200:
            return token, res.text
        token = res.headers.get("token")
        return token, error

    def insertAtlasWorks(self, worksInfo: dict, mobile: str):
        """
        创作图集
        """
        # 登录用户
        token, error = CreateUser.userLoin(mobile)
        if error is not None:
            return error

        # 上传图片
        picBigURL, picUID, error = self.uploadImage(worksInfo["pic_url"], worksInfo["pic_id"], token)
        if error is not None:
            return error

        # 图集创作
        pic = dict()
        pic["pic_id"] = picUID
        pic["title"] = ""
        pic["format"] = "JPG"
        pic["pic_url"] = picBigURL
        pic["label"] = worksInfo["pic_label"]

        works = dict()
        works["title"] = worksInfo["pic_title"]
        works["label"] = worksInfo["pic_label"]
        works["pic_list"] = [pic]

        headers = {
            "Content-Type": "application/json",
            "token": token
        }
        res = requests.post(self.url2, json=works, headers=headers)
        if res.status_code != 200:
            return res.text

        # 发布审核
        worksId = res.json().get("data").get("works_id")
        error = self.insertAtlasRelease(token, worksId)
        if error is not None:
            return error
        # # 售卖申请
        # error = self.insertAtlasSell(token, worksId)
        # if error is not None:
        #     return error
        # # 作品审核
        # error = self.updateAtlasWorksAudit(worksId)
        # if error is not None:
        #     return error
        return ""

    @staticmethod
    def generateUUID():
        return os.urandom(16).hex()
