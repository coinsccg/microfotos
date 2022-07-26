# -*- coding: utf-8 -*-
"""
@Time: 2021/1/26 10:05
@Auth: money
@File: user.py
"""
import base64
import os
import time
import random
import hashlib
import json

import requests
import xlrd
from xlutils.copy import copy

from upload.config import config
from utils import util


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


class CreateUser(object):
    """
    创建用户账号
    """
    domain = config.DOMAIN  # 域名
    url1 = domain + "/api/v1/user/upload/common"  # 头像
    url2 = domain + "/api/v1/login/account"  # 登录
    password = config.PASSWORD

    def __init__(self, imageExcelName: str, imageExcelSheetName: str):
        self.ImageExcelName = imageExcelName
        self.ImageExcelSheetName = imageExcelSheetName
        self.mongo = util.MongoDB(None)
        self.client = self.mongo.client["local_writer"]["microfigure"]

    def getUserImage(self, index: int):
        url = self.readUserNickExcel(index)[2]
        res = requests.get(url)
        return res.content

    def readUserNickExcel(self, index: int):
        excelPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "excel",
                                 self.ImageExcelName + ".xls")
        excel = xlrd.open_workbook(excelPath)
        table = excel.sheet_by_name(self.ImageExcelSheetName)
        rowList = table.row_values(index)
        return rowList

    def writeUserImage(self, mobile: str, index: int):
        excelPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "excel",
                                 self.ImageExcelName + ".xls")
        old = xlrd.open_workbook(excelPath)
        new = copy(old)
        sheet = new.get_sheet(0)
        sheet.write(index, 3, mobile)
        new.save(excelPath)

    def uploadUserImage(self, index: int):
        url = ""
        headers = {
            "token": "eyJtZDVfdG9rZW4iOiAiMDEwNjEzZjVmZGMxZWJjMGEyMTA0MzA5N2FmZjAxZGIiLCAidGltZXN0YW1wIjogMTYxMTY1MzA1NDM3N30="
        }
        content = self.getUserImage(index)
        res = requests.post(self.url1, files=[("pic_list[]", (f"{index}.jpg", content, "image/jpg"))], headers=headers)
        if res.status_code == 200:
            url = res.json().get("data")[0].get("file_path").replace(self.domain, "")
        return url

    def insertUser(self):
        password = self.generatePassword()

        user = User()
        user.uid = ""
        user.nick = ""
        user.sex = "保密"
        user.age = 18
        user.mobile = ""
        user.password = password
        user.head_img_url = ""
        user.background_url = ""
        user.state = 1
        user.account = ""
        user.auth = 0
        user.type = "user"
        user.balance = float(0)
        user.works_num = 0
        user.group = "comm"
        user.label = []
        user.recommend = -1
        tmpTime = int(time.time() * 1000)
        user.create_time = tmpTime
        user.update_time = tmpTime
        user.login_time = tmpTime
        user.sign = "欢迎使用微图，快来更新您的签名吧!"
        with open("./1.txt", "a") as f:
            for i in range(90, 191):
                headImageURL = self.uploadUserImage(i)
                mobile = self.generateMobile()
                nick = self.readUserNickExcel(i)[1]
                self.writeUserImage(mobile, i)
                uuid = os.urandom(16).hex()
                token = self.generateToken(uuid)
                user.uid = uuid
                user.head_img_url = headImageURL.replace(self.domain, "")
                user.nick = nick
                user.token = token
                user.mobile = mobile
                user.account = mobile
                tmp = user.__dict__
                if i > 91:
                    tmp.pop("_id")
                self.client["user"].insert_one(tmp)
                f.write(mobile + "\n")

    @staticmethod
    def userLoin(mobile: str):
        data = {"mobile": mobile, "password": CreateUser.password}
        headers = {"Content-Type": "application/json"}
        res = requests.post(CreateUser.url2, json=data, headers=headers)
        token = ""
        error = None
        if res.status_code == 200:
            token = res.headers.get("token")
        else:
            error = res.content
        return token, error

    @staticmethod
    def generatePassword():
        return base64.b64encode(str(config.PASSWORD).encode()).decode()

    @staticmethod
    def generateMobile():
        # return "133" + str(random.randint(10000000, 99999999)) # 图集数据账号
        return "144" + str(random.randint(10000000, 99999999))  # 文章数据账号

    @staticmethod
    def generateToken(uuid: str):
        md5_token = hashlib.md5(str({"uid": uuid}).encode()).hexdigest()
        data = {"md5_token": md5_token, "timestamp": int(time.time() * 1000)}
        return base64.b64encode(json.dumps(data).encode()).decode()


if __name__ == '__main__':
    demo = CreateUser("头像昵称", "Sheet1")
    demo.insertUser()
