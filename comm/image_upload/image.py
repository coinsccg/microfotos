# -*- coding: utf-8 -*-
"""
@Time: 2021/1/28 16:53
@Auth: money
@File: image.py
"""
import requests
import json
from comm.config.config import USERNAME
from comm.config.config import PASSWORD
from constant.constant import DOMAIN, ARTICLE_TEXT_MAX, WORKS_TITLE_MAX


class ImageUpload(object):
    """
    图文上传
    """
    url = DOMAIN + "/api/v1/login/account"  # 登录
    url3 = DOMAIN + "/api/v1/user/works/batch"  # 发布审核

    @staticmethod
    def userLoin():
        data = {"mobile": USERNAME, "password": PASSWORD}
        headers = {"Content-Type": "application/json"}
        res = requests.post(ImageUpload.url, json=data, headers=headers)
        token = ""
        error = "登录成功"
        if res.status_code == 200:
            tmpData = res.json()
            if tmpData.get("code") == 0:
                token = res.headers.get("token")
            else:
                error = "服务器异常"
        else:
            error = "服务器异常"
        return token, error

    @staticmethod
    def insertAtlasRelease(token: str, worksId: str):
        """
        发布审核
        """
        headers = {
            "token": token
        }
        data = {
            "uid": worksId
        }
        res = requests.post(ImageUpload.url3, json=data, headers=headers)
        error = None
        if res.status_code != 200:
            error = res.text
        return error

    @staticmethod
    def paramFormatVerify(title, content, cover):

        # 参数校验
        error = None
        tmpContent = {}
        if not content:
            error = "缺少正文"
        elif not isinstance(content, str):
            error = "正文格式错误"
        elif len(content) > ARTICLE_TEXT_MAX:
            error = f"正文上限{ARTICLE_TEXT_MAX}个字符"
        elif len(title) > WORKS_TITLE_MAX:
            error = f"标题上限{WORKS_TITLE_MAX}个字符"
        elif not cover:
            error = "缺少封面"
        try:
            tmpContent = json.loads(content)
        except Exception as e:
            error = "正文格式错误"
        if error:
            return error
        if not isinstance(tmpContent, dict):
            error = "正文格式错误"
        if len(tmpContent["content"]) == 0:
            error = "正文格式错误"
        for i in tmpContent["content"]:
            if "text" not in i:
                error = "缺少text字段"
            elif "image_url" not in i:
                error = "缺少image_url字段"
            elif "image_width" not in i:
                error = "缺少image_width字段"
            elif "image_height" not in i:
                error = "缺少text_height字段"
            elif "type" not in i:
                error = "缺少type字段"
        return error
