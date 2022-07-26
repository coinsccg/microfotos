# -*- coding: utf-8 -*-
"""
@Time: 2021/1/26 10:06
@Auth: money
@File: video.py
"""
import os
import random
import json
import requests
import copy

from upload.config.config import DOMAIN, ADMIN_PASSWORD


class ReadTemplateJsonData(object):
    """
    读取模板json数据
    """

    fileName = [1, 2, 3, 4, 5, 6, 7, 8]

    @staticmethod
    def readJsonFile():
        """
        读取json文件
        """
        dirPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        randomFileIndex = ReadTemplateJsonData.fileName[random.randint(0, 7)]
        jsonFilePath = os.path.join(dirPath, "json", "{}.json".format(randomFileIndex))
        with open(jsonFilePath, "r", encoding="utf-8") as f:
            content = f.read()
        jsonFile = json.loads(content)
        jsonFileCopy = copy.deepcopy(jsonFile)
        return jsonFile, jsonFileCopy


class VideoWorksUpload(object):
    """
    影集作品上传
    """

    def __init__(self, cover_id, title, label, pic_list, me_id, tpl_obj):
        self.cover_id = cover_id
        self.title = title
        self.label = label
        self.pic_list = pic_list
        self.me_id = me_id
        self.tpl_obj = tpl_obj

    def videoWorksUpload(self, url: str, token: str):
        videoUploadParam = dict()
        videoUploadParam["cover_id"] = self.cover_id
        videoUploadParam["title"] = self.title
        videoUploadParam["label"] = self.label
        videoUploadParam["pic_list"] = self.pic_list  # array [{"uid": , "title": , "label": , "pic_url": , ...}, ...]
        videoUploadParam["me_id"] = self.me_id
        videoUploadParam["tpl_obj"] = self.tpl_obj
        headers = {
            "token": token
        }
        res = requests.post(url, json=videoUploadParam, headers=headers)
        return res.json().get("data").get("works_id")


class VideoMake(object):
    """
    影集模板制作
    """
    url1 = DOMAIN + "/api/v1/user/pic/resize"  # 图片压缩
    url2 = DOMAIN + "/api/v1/user/local/upload"  # 图片
    url3 = "https://rosetta.tt.cn/mf/qt/images"  # 微图客户图片获取地址
    url4 = DOMAIN + "/api/v1/login/account"  # 用户登录
    url5 = "http://cloud.microfotos.cn/1.1/addBatch"  # 上传影集模板
    url6 = DOMAIN + "/api/v1/user/video/create"  # 影集上传
    url7 = DOMAIN + "/api/v1/user/works/batch"  # 发布审核
    mobileList = ["14440627651", "14474029762", "14440375946", "14480814279", "14474239269", "14422248578",
                  "14415575144", "14482215881", "14461304737", "14412625704", "14448874522", "14457948758",
                  "14422387553", "14424327150", "14475771729", "14475902382", "14424191155", "14413318533",
                  "14454501215", "14441918384", "14495706148", "14459312710", "14465310086", "14455609514",
                  "14410181374", "14452158501", "14431846399", "14435618801", "14469657813", "14439962170"
                  ]

    def __init__(self, pageNo: int):
        # self.pagesList = jsonFile["page_value"]
        self.pageNo = pageNo

    @staticmethod
    def getItemCanReplace(objectsList: list) -> list:
        """
        获取可以替换的节点
        :param objectsList: item_object对象列表
        """
        spritesList = []
        for obj in objectsList:
            if obj["item_type"] == 18:
                canReplace = 0
                picReplaceTmp = obj.get("pic_replace")
                if picReplaceTmp is not None:
                    canReplace = picReplaceTmp
                if canReplace == 0:
                    spritesList.append(obj)

        # pic_replaceindex默认倒叙排序
        spritesList = sorted(spritesList, key=lambda x: x.get("pic_replaceindex") if x.get("pic_replaceindex") else 0,
                             reverse=True)
        # item_layer默认倒叙排序
        spritesList = sorted(spritesList, key=lambda x: x.get("item_layer") if x.get("item_layer") else 0, reverse=True)

        return spritesList

    def replaceImage(self, picURLList: list, pagesList: list):
        """
        单页替换图片
        :param picURLList: 被压缩图片的url列表
        :param pagesList: 模板["page_value"]
        """
        for i in pagesList:
            objectsList = i["item_object"]
            spritesList = self.getItemCanReplace(objectsList)
            picInfoLength = len(picURLList)
            n = 0
            for j in spritesList:
                j["item_val"] = picURLList[n % picInfoLength]
                j["isReset"] = True
                n += 1

    def getSizeList(self, pagesList: list) -> list:
        """
        获取模板中可替换图片的尺寸列表
        :param pagesList: 模板["page_value"]
        """
        sizeList = []
        for i in pagesList:
            objectsList = i["item_object"]
            spritesList = self.getItemCanReplace(objectsList)
            for j in spritesList:
                sizeList.append({"width": float(j["item_width"]), "height": float(j["item_height"])})
        return sizeList

    @staticmethod
    def userLoin():
        APP_USERNAME = random.choice(VideoMake.mobileList)
        data = {"mobile": APP_USERNAME, "password": ADMIN_PASSWORD}
        headers = {"Content-Type": "application/json"}
        res = requests.post(VideoMake.url4, json=data, headers=headers)
        token = ""
        error = None
        if res.status_code == 200:
            token = res.headers.get("token")
        else:
            error = res.content
        return token, error

    def uploadImage(self, imageURL: str, imageId: int, token: str):
        """
        上传图片
        """
        res1 = requests.get(imageURL)
        headers = {
            "token": token
        }
        res2 = requests.post(self.url2, files=[("pic_list[]", (f"{imageId}.jpg", res1.content, "image/jpg"))],
                             headers=headers)
        error = None
        picBigURL = ""
        picUID = ""
        if res2.status_code == 200:
            if res2.json().get("code") == 0:
                data = res2.json().get("data")[0]
                picBigURL = data["zbig_pic_url"]
                picUID = data["uid"]
            else:
                error = "image invalid: " + res2.json().get("msg")
        else:
            error = res2.text
        return picBigURL, picUID, error

    def getRequestImageFromCustomToMicro(self):
        """
        从微图客户服务器获取图片并上传
        """
        # 登录获取token

        params = dict()

        params["pageNum"] = self.pageNo
        params["pageSize"] = 100
        res = requests.get(self.url3, params=params)
        resImageList = res.json().get("data").get("page").get("content")
        random.shuffle(resImageList)
        for i in range(1, 11):
            # 加载模板
            token, _ = VideoMake.userLoin()
            jsonFile, jsonFileCopy = ReadTemplateJsonData.readJsonFile()
            startIndex = (i - 1) * 10
            endIndex = i * 10
            imageInfoList = []
            for d in resImageList[startIndex:endIndex]:
                imageURL = d.get("downloadUrl")
                imageId = d.get("picId")
                imageLabel = d.get("tagStr").split(",")
                title = d.get("picTitle")

                # 上传图片
                picBigURL, picUID, error = self.uploadImage(imageURL, imageId, token)
                imageInfoList.append(
                    {"pic_url": picBigURL, "uid": picUID, "label": imageLabel, "title": title, "format": "JPG",
                     "type": ""})
            imageURLList = [j["pic_url"] for j in imageInfoList]
            sizeList = self.getSizeList(jsonFile["page_value"])
            for k, v in enumerate(sizeList):
                v["url"] = imageURLList[k % len(imageURLList)]
                v["width"] = int(v["width"])
                v["height"] = int(v["height"])
            handleImageURLList = self.getRequestPhotoResize(sizeList, token)  # 压缩图片
            self.replaceImage(handleImageURLList, jsonFile["page_value"])

            # 上传影集
            meId = VideoMake.uploadVideoTemplateToMe(jsonFile)
            videoWorksUpload = VideoWorksUpload(imageInfoList[1]["uid"], imageInfoList[1]["title"], [],
                                                imageInfoList, meId,
                                                json.dumps(jsonFileCopy, ensure_ascii=False, separators=(',', ':')))
            worksId = videoWorksUpload.videoWorksUpload(VideoMake.url6, token)

            # 发布审核
            self.insertAtlasRelease(token, worksId=worksId)

    def getRequestPhotoResize(self, imageInfo: list, token: str):
        """
        将图片进一步压缩
        :param imageInfo: 待压缩图片信息
        :param token: 请求凭证
        """
        headers = {
            "token": token
        }
        imageInfoListDict = {
            "url_list": imageInfo
        }

        res = requests.post(self.url1, json=imageInfoListDict, headers=headers)
        url = ""
        if res.status_code == 200:
            url = res.json().get("data")
        return url

    def labelBestCombination(self):
        """
        每10张图片组合成一个影集
        """
        imageInfoList, token = self.getRequestImageFromCustomToMicro()
        random.shuffle(imageInfoList)
        for i in range(1, 11):
            # 加载模板
            jsonFile, jsonFileCopy = ReadTemplateJsonData.readJsonFile()

            startIndex = (i - 1) * 10
            endIndex = i * 10
            imageInfoListTmp = imageInfoList[startIndex:endIndex]
            imageURLList = [j["pic_url"] for j in imageInfoListTmp]
            sizeList = self.getSizeList(jsonFile["page_value"])
            for k, v in enumerate(sizeList):
                v["url"] = imageURLList[k % len(imageURLList)]
                v["width"] = int(v["width"])
                v["height"] = int(v["height"])
            handleImageURLList = self.getRequestPhotoResize(sizeList, token)  # 压缩图片
            self.replaceImage(handleImageURLList, jsonFile["page_value"])

            # 上传影集
            meId = VideoMake.uploadVideoTemplateToMe(jsonFile)
            videoWorksUpload = VideoWorksUpload(imageInfoListTmp[1]["uid"], imageInfoListTmp[1]["title"], [],
                                                imageInfoListTmp, meId,
                                                json.dumps(jsonFileCopy, ensure_ascii=False, separators=(',', ':')))
            worksId = videoWorksUpload.videoWorksUpload(VideoMake.url6, token)

            # 发布审核
            self.insertAtlasRelease(token, worksId=worksId)

    @staticmethod
    def uploadVideoTemplateToMe(templateJsonStr: dict):
        """
        :param templateJsonStr: 模板字典
        """
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "x-lc-sign": "18f05190729df0c69b4e38782b73f5d9,1596435388",
            "Accept-Encoding": "gzip",
            "Content-Length": "40909",
            "x-lc-id": "hf3jpecovudrg8t7phw3xbt1osqfrmfhnwu22xs8jo1ia3hn",
            "Host": "cloud.microfotos.cn"
        }
        res = requests.post(VideoMake.url5, json=templateJsonStr, headers=headers)
        tplId = ""
        if res.status_code == 200:
            tplId = res.json().get("success").get("TplId")
        return tplId

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
        res = requests.post(self.url7, json=data, headers=headers)
        error = None
        if res.status_code != 200:
            error = res.text
        return error


if __name__ == '__main__':
    demo = VideoMake(2)
    demo.getRequestImageFromCustomToMicro()
