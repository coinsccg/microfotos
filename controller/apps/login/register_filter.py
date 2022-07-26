# -*- coding: utf-8 -*-
"""
@Time: 2021/2/19 9:31
@Auth: money
@File: register_filter.py
"""
import time

from filter.pic import pic
from filter.user import user_info
from utils.upload_img import upload
from constant.constant import FILTER_KW


class RegisterFilter(object):
    """
    第三方注册昵称头像过滤
    """

    officialKeyword = FILTER_KW

    def __init__(self, nick: str, icon: str):
        self.nick = nick
        self.icon = icon

    def nickFilter(self):
        userInfoFilter = user_info.UserInfoFilter()
        rest, err = userInfoFilter.sendRequest("nick", "001", self.nick)
        if rest:
            nick = self.nick
            for i in self.officialKeyword:
                nick = nick.replace(i, "", -1)
        else:
            nick = "用户" + str(int(time.time()))[2:]
        return nick

    def imageFilter(self):
        imgFilter = pic.ImageFilter()
        result, err = imgFilter.sendRequest("dynamic", "001", self.icon)
        if result:
            uploadImage = upload.UploadImage()
            iconRelativePath = uploadImage.imgDownLoadAndUpload(self.icon)
            head_img_url = iconRelativePath
        else:
            head_img_url = ""
        return head_img_url
