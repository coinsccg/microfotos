# -*- coding: utf-8 -*-
"""
@Time: 2021/1/26 10:06
@Auth: money
@File: image.py
"""


class ImageUpload(object):
    """
    图片作品上传类
    """

    def __init__(self):
        self.url1 = "http://m.microfotos.cn/api/v1/user/creation/atlas"  # 图集制作
        self.url2 = "http://m.microfotos.cn/api/v1/user/upload/common"  # 图片上传

    @staticmethod
    def getImageInfo(d: dict):
        """
        对接微图客户图片
        """
        pass

    @staticmethod
    def uploadImage(self):
        """
        微图APP图片通用接口上传
        """

    def insertImageWorks(self):
        pass
