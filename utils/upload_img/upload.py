# -*- coding: utf-8 -*-
"""
@Time: 2021/2/8 15:25
@Auth: money
@File: upload.py
"""
import os
import shutil
import time
import datetime
import hashlib
import requests

import redis
import cv2
# import pyheif # heic转jpg pip install pyheif
from PIL import Image

from utils.upload_img.config import VIDEO_CHUNK_SIZE


class UploadImage(object):
    """
    图片上传
    """

    @staticmethod
    def uploadImage(imageList: list):
        """
        :param imageList: 图片列表
        return
        """

        relativeIconPathList = []
        error = None
        try:
            for img in imageList:
                imgExt = img.filename.rsplit(".")[-1].rsplit("\"")[0]
                imgDirRootPath = os.path.join(os.getcwd(), "statics", "files")
                date = datetime.datetime.now()
                year, month, day = str(date.year), str(date.month), str(date.day)
                imgYMDPath = os.path.join(imgDirRootPath, year, month, day)
                if not os.path.exists(imgYMDPath):
                    os.makedirs(imgYMDPath)

                uuid = hashlib.md5(str(time.time()).encode("utf-8")).hexdigest()
                imgAbsPath = os.path.join(imgYMDPath, uuid + f".{imgExt}")

                # 将heic格式转成jpg
                if imgExt == "HEIC":
                    imgByte = pyheif.read_heif(img.read())
                    out = Image.frombytes(mode=imgByte.mode, size=imgByte.size, data=imgByte.data)
                    out.save(imgAbsPath.replace(imgExt, "jpg"), "JPEG")
                    imgExt = "jpg"
                else:
                    with open(imgAbsPath, "wb") as f:
                        f.write(img.read())
                relativeIconPath = os.path.join("/", year, month, day, uuid + ".{}".format(imgExt))
                relativeIconPathList.append({"file_path": relativeIconPath, "file_extension": imgExt})
        except Exception as e:
            error = e
        finally:
            return relativeIconPathList, error

    @staticmethod
    def imgEqualScale(imgList):
        """
        图片等比例缩放
        :imgList: 待缩放图片对象列表，例如：{url: , width: , height: }
        """

        imgURLList = []
        for img in imgList:
            url = img["url"]
            rootPath = os.getcwd()
            imgAbsPath = os.path.join(rootPath, "statics", "files", url)
            imgExt = imgAbsPath.split(".")[-1]

            date = datetime.datetime.now()
            year, month, day = str(date.year), str(date.month), str(date.day)
            uuid = hashlib.md5(str(time.time()).encode("utf-8")).hexdigest()
            imgAbsDir = os.path.join(rootPath, "statics", "files", year, month, day)
            if not os.path.exists(imgAbsDir):
                os.makedirs(imgAbsDir)

            #  # 等比例缩放原图
            im = Image.open(imgAbsPath)
            imgPath = os.path.join(imgAbsDir, uuid + "{}".format(imgExt))
            tplWidth, tplHeight = img.get("width"), img.get("height")
            originWidth, originHeight = im.size
            scaleX = tplWidth / originWidth
            scaleY = tplHeight / originHeight
            if scaleX > scaleY:
                originHeightTmp = int(scaleX * originHeight)
                out = im.resize((tplWidth, originHeightTmp), Image.ANTIALIAS)
                cropped = out.crop((0, int((originHeightTmp - tplHeight) / 2), tplWidth,
                                    tplHeight + int((originHeightTmp - tplHeight) / 2)))
                cropped.save(imgPath)
            elif scaleX < scaleY:

                originWidthTmp = int(scaleY * originWidth)
                out = im.resize((originWidthTmp, tplHeight), Image.ANTIALIAS)
                cropped = out.crop((int((originWidthTmp - tplWidth) / 2), 0,
                                    tplWidth + int((originWidthTmp - tplWidth) / 2), tplHeight))
                cropped.save(imgPath)
            else:
                out = im.resize((tplWidth, tplHeight), Image.ANTIALIAS)
                out = out.convert("RGB")
                out.save(imgPath)
            imgURLList.append(os.path.join("/", year, month, day, uuid + "{}".format(imgExt)))
        return imgURLList

    @staticmethod
    def imgDownLoadAndUpload(imgUrl: str):
        """
        下载第三方图片并上传
        :param imgUrl: 头像
        """

        res = requests.get(imgUrl)
        date = datetime.datetime.now()
        year, month, day = str(date.year), str(date.month), str(date.day)
        imgDir = os.path.join(os.getcwd(), "statics", "files", year, month, day)
        uuid = os.urandom(16).hex()
        if not os.path.exists(imgDir):
            os.makedirs(imgDir)
        imgPath = os.path.join(imgDir, uuid + ".jpg")
        with open(imgPath, "wb") as f:
            f.write(res.content)
        return os.path.join("/", year, month, day, uuid + ".jpg")


class UploadVideo(object):
    """
    视频分片上传
    """

    def __init__(self):
        self.conn = redis.Redis(decode_responses=True, password="gli123456")
        # self.conn = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

    def videoChunkInit(self):
        """
        分片上传初始化
        return videoId/chunkCount 视频id/分片总数
        """
        # chunkCount = videoSize / VIDEO_CHUNK_SIZE + 1
        videoId = os.urandom(16).hex()
        # self.conn.set(videoId, chunkCount, ex=5 * 60)
        return videoId, VIDEO_CHUNK_SIZE

    def videoChunkUpload(self, videoId: str, index: int, chunk):
        """
        分片上传函数
        :param videoId: 视频id
        :param index: 当前分片索引
        :param chunk: 当前分片文件流
        """
        chunkDirTmpPath = os.path.join(os.getcwd(), "statics", "files", videoId)
        if not os.path.exists(chunkDirTmpPath):
            os.makedirs(chunkDirTmpPath)

        with open(os.path.join(chunkDirTmpPath, str(index)), "wb") as f:
            f.write(chunk.read())
        chunkIndexList = self.conn.lrange(videoId, 0, -1)
        if index in chunkIndexList:
            return chunkIndexList
        self.conn.lpush(videoId, index)
        return None

    def videoChunkMerge(self, videoId: str, chunkCount: int, videoExt: str):
        """
        :param videoId: 视频id
        :param chunkCount: 视频总分片数
        :param videoExt: 视频扩展，mp4
        """
        date = datetime.datetime.now()
        year, month, day = str(date.year), str(date.month), str(date.day)
        chunkIndexListLen = self.conn.llen(videoId)
        chunkDirTmpPath = os.path.join(os.getcwd(), "statics", "files", videoId)
        if chunkCount != chunkIndexListLen:
            shutil.rmtree(chunkDirTmpPath)
            return None
        absDirPath = os.path.join(os.getcwd(), "statics", "files", year, month, day)
        if not os.path.exists(absDirPath):
            os.makedirs(absDirPath)
        relativePath = os.path.join(year, month, day, videoId + ".{}".format(videoExt))
        with open(os.path.join(os.getcwd(), "statics", "files", relativePath), "ab") as f:
            for i in range(0, chunkCount):
                with open(os.path.join(chunkDirTmpPath, str(i)), "rb") as chunk:
                    f.write(chunk.read())
                os.remove(os.path.join(chunkDirTmpPath, str(i)))
            os.rmdir(chunkDirTmpPath)
        return "/" + relativePath

    def videoFrame(self, videoPath: str):
        """
        视频取真
        :param videoPath: 视频相对路径
        """
        videoCapture = cv2.VideoCapture(os.path.join(os.getcwd(), "statics", "files") + videoPath)

        i = 0
        while videoCapture.isOpened():
            if i == 0:
                success, frame = videoCapture.read()
                if success:
                    uid = os.urandom(16).hex()
                    date = datetime.datetime.now()
                    year, month, day = str(date.year), str(date.month), str(date.day)
                    relativePath = os.path.join(year, month, day, uid + ".jpg")
                    imgPath = os.path.join(os.getcwd(), "statics", "files", relativePath)
                    cv2.imwrite("{}.jpg".format(uid), frame)
                    with open(imgPath, "wb") as f:
                        with open("{}.jpg".format(uid), "rb") as file:
                            f.write(file.read())
                    os.remove("{}.jpg".format(uid))
                    im = Image.open(imgPath)
                    width, height = im.size
                    return "/" + relativePath, width, height


class UploadMusic(object):
    """
    音乐上传
    """

    @staticmethod
    def upload(file):
        date = datetime.datetime.now()
        year, month, day = str(date.year), str(date.month), str(date.day)
        uuid = os.urandom(16).hex()
        videoDirPath = os.path.join(os.getcwd(), "statics", "files", year, month, day)
        absPath = os.path.join(videoDirPath, uuid + ".mp3")
        if not os.path.exists(videoDirPath):
            os.makedirs(videoDirPath)
        with open(absPath, "wb") as f:
            f.write(file.read())
        return os.path.join("/", year, month, day, uuid + ".mp3")


if __name__ == '__main__':
    demo = UploadVideo()
    demo.videoFrame("\\2021\\2\\24\\4a81989de451a755e1764aa8755ad354.mp4")