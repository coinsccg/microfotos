# -*- coding: utf-8 -*-
"""
@Time: 2021/1/26 10:08
@Auth: money
@File: images.py
"""
import os
import time
import random

import requests
import xlrd

from upload.api.image import ImageUpload
from upload.api.atlas import AtlasWorks


class GetImages(object):
    """
    对接微图客户图片类
    """

    def __init__(self):
        self.url = "https://rosetta.tt.cn/mf/qt/images"
        self.tableName = "微图本地化映射"
        self.sheetName = "分类"
        self.constantAccount = ["13348594594", "13361474328", "13354862828", "13385197738", "13321608876",
                                "13382485045", "13367417279", "13376690941"]

    def getImageList(self, index: int):
        i = index
        tmpPicId = ""
        logPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            atlasWorks = AtlasWorks()
            params = dict()
            while 1:
                if i > index:
                    break
                params["pageNum"] = i
                params["pageSize"] = 100
                res = requests.get(self.url, params=params)
                tmpDict = {}
                for d in res.json().get("data").get("page").get("content"):

                    tmpPicId = d.get("picId")

                    picLabelList = d.get("tagStr").split(",")

                    # 读取用户mobile
                    mobile = self.getExcel(self.tableName, self.sheetName, picLabelList)
                    if mobile == "":
                        mobile = random.choice(self.constantAccount)

                    # 对接微图APP
                    tmpDict["pic_title"] = d.get("picTitle")
                    tmpDict["pic_label"] = picLabelList
                    tmpDict["pic_url"] = d.get("downloadUrl")
                    tmpDict["pic_id"] = tmpPicId
                    updateTime = d.get("updateTime")
                    tmpDict["create_time"] = updateTime
                    tmpDict["create_time"] = updateTime
                    result = atlasWorks.insertAtlasWorks(tmpDict, mobile)
                    if result != "":
                        raise Exception(result)

                if res is None:
                    break

                i += 1
        except Exception as e:
            with open(os.path.join(logPath, "log", "log.txt"), "a") as f:
                f.write(str(e) + f"pageNo: {i}  pageSize: {i * 10}  picId: {tmpPicId}" + ";\n")

    def getStaticImage(picId, imageDownURL):
        # 创建临时目录
        dirPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpDir = os.path.join(dirPath, "tmp", f"{picId}")
        if not os.path.exists(tmpDir):
            os.makedirs(tmpDir)

        res = requests.get(imageDownURL)
        with open(os.path.join(tmpDir, f"{picId}.png"), "wb") as f:
            f.write(res.content)
        return os.path.join(tmpDir, f"{picId}.png")

    @staticmethod
    def getExcel(excelName: str, sheetName: str, label: list):
        excelPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "excel",
                                 excelName + ".xlsx")
        excel = xlrd.open_workbook(excelPath)
        table = excel.sheet_by_name(sheetName)

        mobile = ""
        for i in range(1, table.nrows):
            rowList = table.row_values(i)
            tagLabelList: list = rowList[3].split("，")
            mobile = str(int(rowList[5]))
            if len(list(set(tagLabelList).intersection(set(label)))) >= 1:
                break
        return mobile


if __name__ == '__main__':
    # demo = GetImages()
    # demo.getImageList()
    pass
