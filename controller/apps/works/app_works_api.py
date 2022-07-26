# -*- coding: utf-8 -*-
"""
@File: app_works_api
@Time: 2020-06-30
@Auth: money
"""
import re
import time
import datetime
from bson.son import SON

import jieba
from flask import g
from flask import request

from constant import constant
from middleware.auth import response, verifyJWT
from initialize import log
from initialize import client
from initialize import stopword
from utils.util import IdCardAuth
from utils.util import UploadSmallFile
from utils.util import generate_uid
from utils.util import genrate_file_number
from utils.util import GenerateImage
from utils.upload_img import upload
from dao.app.works import material
from dao.app.works import works
from filter.pic import pic
from filter.user import user_info
from comm.image_upload.image import ImageUpload
from werkzeug.datastructures import FileStorage


def pic_sell_apply(uid, tag, code, user_id, price_item):
    """
    图集、影集图片售卖API
    :param uid: 作品id
    :param tag: 标签
    :param code： 是否平台定价
    :param user_id: 用户id
    :param price_item: 价格信息
    """

    # 更新图片作品信息
    temp_doc1 = client["portrait"].find_one({"works_id": uid, "user_id": user_id})
    temp_doc2 = client["products"].find_one({"works_id": uid, "user_id": user_id})
    condition = {
        "$set": {
            "state": 4, "tag": tag, "is_portrait": True if temp_doc1 else False,
            "is_products": True if temp_doc2 else False
        }
    }
    doc = client["works"].update({"uid": uid, "user_id": user_id}, condition)
    if doc["n"] == 0:
        return response(msg="Update failed.", code=1, status=400)

    # 为S、M、L、扩大授权添加价格
    doc = client["pic_material"].find_one({"works_id": uid})
    if code == 1:
        for i in price_item:
            if i["price"] > constant.PRICE_MAX:
                return response(msg=f"售价上限{constant.PRICE_MAX}元", code=1)
            if len(i["format"]) == 7:
                client["price"].update(
                    {"format": i["format"][:1], "pic_id": doc.get("uid")},
                    {"$set": {"price": i["price"], "type": code}}
                )
            else:
                client["price"].update(
                    {"format": "扩大授权", "pic_id": doc.get("uid")},
                    {"$set": {"price": i["price"]}}
                )
    else:
        cursor = client["price"].find({"uid": "001"})
        for i in cursor:
            client["price"].update(
                {"format": i.get("format"), "pic_id": doc.get("uid")},
                {"$set": {"price": i.get("price"), "type": code}}
            )
    # 改变素材库中works_state
    client["pic_material"].update({"works_id": uid}, {"$set": {"works_state": 1}})


def altas_pic_create_works_api(works_uid, user_id, title, label, pic_list):
    """图集、影集图片创作API
    """
    # 分词建立全文索引
    # 去除停顿词
    rst = list(jieba.cut(title, cut_all=False)) + label
    all_kw = [i for i in rst if i not in stopword]
    # 拼接字符串
    index_str = " ".join(all_kw)
    # 制作图片作品
    pic_title = pic_list[0]["title"]
    pic_label = pic_list[0].get("label")
    pic_id = [pic_list[0]["pic_id"]]  # 图片id
    pic_format = pic_list[0]["format"]
    pic_url = pic_list[0]["pic_url"].replace(constant.DOMAIN, "")
    pic_info = {
        "pic_id": pic_id[0], "title": pic_title, "label": pic_label, "pic_url": pic_url,
        "format": pic_format or "JPG"
    }
    number = genrate_file_number()
    keyword = list(jieba.cut(pic_title))
    # 判断该图是否已经制作过趣图作品
    doc = client["works"].find_one({"pic_id": pic_id[0], "state": 2, "type": "tp"})
    if doc:
        return response(msg="请勿重复制作图片作品", code=1)
    temp_doc = client["price"].find_one({"pic_id": pic_id[0]})
    price_id = temp_doc["uid"]
    condition = {
        "uid": works_uid, "user_id": user_id, "pic_id": pic_id, "type": "tp", "number": number,
        "format": pic_format.upper(), "title": pic_title, "keyword": keyword, "label": label, "state": 0,
        "recommend": -1, "is_portrait": False, "is_products": False, "pic_num": 1, "like_num": 0,
        "comment_num": 0, "tag": "商", "share_num": 0, "browse_num": 0, "sale_num": 0, "index_text": index_str,
        "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000), "price_id": price_id,
        "pic_info": [pic_info], "browse_time": int(time.time() * 1000)
    }
    client["works"].insert(condition)

    # 更新素材表中的状态
    client["pic_material"].update(
        {"user_id": user_id, "uid": pic_id[0]},
        {"$set": {"works_id": works_uid, "works_state": 0}}
    )


def altas_pic_works_statisticals_api(user_id, label):
    """图集、影集图片制作、售卖统计
    :param user_id: 用户id
    :param label: 标签
    """

    # 统计
    # 当前day天
    dtime = datetime.datetime.now()
    time_str = dtime.strftime("%Y-%m-%d") + " 0{}:00:00".format(0)
    timeArray = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    today_stamp = int(time.mktime(timeArray.timetuple()) * 1000)
    doc = client["user_statistical"].find_one({"user_id": user_id, "date": today_stamp})
    if doc:
        doc = client["user_statistical"].update(
            {"user_id": user_id, "date": today_stamp},
            {"$inc": {"works_num": 1}, "$set": {"update_time": int(time.time() * 1000)}}
        )
        if doc["n"] == 0:
            return response(msg="Update failed.", code=1, status=400)
    else:
        condition = {
            "user_id": user_id, "date": today_stamp, "works_num": 1, "sale_num": 0, "browse_num": 0,
            "amount": float(0), "like_num": 0, "goods_num": 0, "register_num": 0, "comment_num": 0, "share_num": 0,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }
        client["user_statistical"].insert(condition)
    # 历史标签表和标签表
    for i in label:
        # 记录历史标签
        condition = {
            "user_id": user_id, "label": i, "state": 1, "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        doc = client["history_label"].find_one({"user_id": user_id, "label": i})
        if not doc:
            client["history_label"].insert(condition)


def ssh_connect_mongo():
    """ssh远程连接数据库"""
    from sshtunnel import SSHTunnelForwarder  # pip install sshtunnel
    import pymongo
    server = SSHTunnelForwarder(
        ssh_address_or_host="120.26.218.247",  # 远程服务器IP
        ssh_username="root",  # 远程服务器用户名
        ssh_password="www.gli.cn123!!@#",  # 远程服务器密码
        remote_bind_address=("127.0.0.1", 27017)  # 远程服务器mongo绑定的端口
    )
    server.start()
    client = pymongo.MongoClient("127.0.0.1", server.local_bind_port)
    client_me = client["Lean"]
    return client_me


def pic_upload_api(user_id):
    """
    图片上传调用API
    :param user_id: 用户id
    """
    error = None
    data_list = []
    try:
        fileData = request.files.to_dict()
        image = fileData.get("pic_list[]")
        # 校验
        error = None
        if not image:
            error = "PicList is required."
        elif not isinstance(image, FileStorage):
            error = "pic_list[] element type invalid"

        if error:
            raise Exception(error)

        file = UploadSmallFile(log)
        context = file.upload_file("pic_list[]", "files", user_id)
        if context["code"] == 0:
            error = context["msg"]
        data_list = context["data"]
    except Exception as e:
        error = e
    finally:
        return data_list, error


def post_material_upload_common():
    """
    素材上传通用接口
    """
    try:

        user_id = g.user_data["user_id"]
        pic_list = request.files.getlist("pic_list[]")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not pic_list:
            error = "PicList is required."

        if error:
            return response(msg=error, code=1, status=400)

        # data = pic_upload_api(user_id)
        data = g.data
        if g.error is not None:
            return response(msg=str(g.error), code=1)
        for i in data:
            file_path = i["file_path"]
            context = GenerateImage.generate_image_origin(i, "files")
            file_path = context["file_path_b"]
            i["file_path"] = constant.DOMAIN + file_path
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_audio_upload_common():
    """
    音频上传通用接口
    """
    try:

        user_id = g.user_data["user_id"]
        audio_list = request.files.getlist("audio_list[]")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not audio_list:
            error = "AudioList is required."

        if error:
            return response(msg=error, code=1, status=400)

        file = UploadSmallFile(log)
        context = file.upload_file("audio_list[]", "files", user_id)
        if context["code"] == 0:
            return response(msg=context["msg"], code=1, status=400)
        data = context["data"]
        for i in data:
            file_path = i["file_path"]
            i["file_path"] = constant.DOMAIN + file_path
            # TODO音频写入me中me_music表
            # from dateutil import parser 
            # date = parser.parse(datetime.datetime.utcnow().isoformat()) # mongo Date格式的时间
            # condition = {"music_path": file_path, "muisc_upload_user": user_id, "createAt": date, "updateAt": date}
            # client_me = ssh_connect_mongo()
            # client_me["me_music"].insert(condition)
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_pic_material_upload():
    """
    素材上传接口
    """
    try:

        user_id = g.user_data["user_id"]
        user_info = g.user_data["user_info"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # 图片上传
        data_list, error = pic_upload_api(user_id)
        if error is not None:
            return response(msg=str(error), code=1)
        # data_list = g.data
        # 图片入库
        tmp, error = material.materialUpload(data_list, user_info, user_id)
        if error:
            raise Exception(error)

        return response(data=tmp)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_material():
    """
    获取图片素材库
    """
    try:

        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")

        # 校验
        error = None
        if not user_id:
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询
        dataList, error = material.queryMaterialList(user_id, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_history_label(label_max=20):
    """
    用户历史标签
    :param label_max: 标签个数上限
    """
    try:
        # 参数
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        # 查询
        dataList, error = material.queryUserHistoryLabel(user_id, label_max)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_altas_search_label():
    """图集搜索标签接口"""
    keyword_list = []
    try:

        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        keyword = request.args.get("keyword")

        # 校验
        error = None
        if not keyword:
            error = "请输入关键词"
        elif len(keyword) > constant.LABEL_MAX:
            error = f"搜索字数上限{constant.LABEL_MAX}"
        if error:
            return response(msg=error, code=1)

        # 模糊查询
        cursor = client["label"].find({"label": {"$regex": keyword}, "type": "pic"}, {"_id": 0, "label": 1})
        for doc in cursor:
            keyword_list.append(doc["label"])
        if keyword in keyword_list:
            keyword_list = list(set(keyword_list))
            keyword_list.remove(keyword)
            keyword_list.insert(0, keyword)
        return response(data=keyword_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_pic_works_list():
    """创作图集--用户图片作品列表
    :param domain: 域名
    """
    try:
        # 参数
        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")

        # 校验
        error = None
        if not user_id:
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif not content:
            error = "Content is required."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询
        dataList, error = works.queryPicWorksList(user_id, content, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_pic_collect_works(pic_num_max=100):
    """
    图集创作
    :param pic_num_max: 图片上限
    """
    try:

        user_id = g.user_data["user_id"]
        title = request.json.get("title")
        label = request.json.get("label")
        pic_list = request.json.get("pic_list")  # array [{"pic_id": , "title": , "format":, "pic_url": ,}, ...]

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not pic_list:
            error = "pic_list is required."

        if error:
            return response(msg=error, code=1, status=400)

        if len(pic_list) > pic_num_max:
            return response(msg=f"图片上限{pic_num_max}张", code=1)

        works_uid = generate_uid(24)
        # 分词建立全文索引
        # 去除停顿词
        rst = list(jieba.cut(title, cut_all=False)) + label
        all_kw = [i for i in rst if i not in stopword]
        # 拼接字符串
        index_str = " ".join(all_kw)
        if len(pic_list) == 1:
            # 制作图片作品
            pic_id, error = works.createPicWorks(pic_list, works_uid, user_id, label, index_str, title)
            if error:
                return response(msg=str(error), code=1)
        else:
            # 制作图集作品
            if not title:
                return response(msg="Bad Request: Miss param 'title'.", code=1, status=400)
            if len(title) > constant.WORKS_TITLE_MAX:
                return response(msg=f"标题字数上限{constant.WORKS_TITLE_MAX}", code=1)
            pic_id, error = works.createAltasWorks(pic_list, title, works_uid, user_id, label, index_str)
            if error:
                return response(msg=str(error), code=1)

        # 作品统计
        error = works.worksStatistical(user_id)
        if error:
            raise Exception(error)

        # 历史标签表和标签表
        error = works.labelStatistical(user_id, label)
        if error:
            raise Exception(error)

        data = {
            "pic_id": pic_id[0],
            "works_id": works_uid
        }
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_editor_pic_collect_works(pic_num_max=20):
    """
    图集作品编辑
    :param pic_num_max: 图片上限
    """
    try:

        user_id = g.user_data["user_id"]
        title = request.json.get("title")
        label = request.json.get("label")
        pic_list = request.json.get("pic_list")  # array [{"pic_id": , "title": , "format":, "pic_url": ,}, ...]
        works_id = request.json.get("works_id")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksId is required."
        elif not title:
            error = "Title is required."
        elif not pic_list:
            error = "PicList is required."

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if len(pic_list) > pic_num_max:
            error = f"图片上限{pic_num_max}张"
        elif len(title) > constant.WORKS_TITLE_MAX:
            error = f"标题字数上限{constant.WORKS_TITLE_MAX}"

        if error:
            return response(msg=error, code=1)

        # 编辑图集
        error = works.putAltasWorks(pic_list, works_id, title, label)
        if error:
            return response(msg=str(error), code=1)

        # 作品数减1
        error = works.putAltasWorksReduceWorksNum(works_id, user_id)
        if error:
            raise Exception(error)

        # 标签个数修改
        error = works.putLabelNum(works_id, label)
        if error:
            raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_video_collect_works(pic_num_max=30):
    """
    影集创作
    :param pic_num_max: 图片上限
    """
    try:
        # 参数
        user_id = g.user_data["user_id"]
        cover_id = request.json.get("cover_id")
        title = request.json.get("title")
        label = request.json.get("label")
        pic_list = request.json.get("pic_list")  # array [{"uid": , "title": , "label": , "pic_url": , ...}, ...]
        me_id = request.json.get("me_id")
        tpl_obj = request.json.get("tpl_obj")

        # 参数校验
        error = None
        if not user_id:
            error = "User is required."
        elif not title:
            error = "Title is required."
        elif not pic_list:
            error = "PicList is required."
        elif not me_id:
            error = "MeId is required."
        elif not cover_id:
            error = "CoverId is required."
        elif not tpl_obj:
            error = "TplObj is required."

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if len(title) > constant.WORKS_TITLE_MAX:
            error = f"标题字数上限{constant.WORKS_TITLE_MAX}"
        elif len(pic_list) <= 1:
            error = "影集至少2张图片"
        elif len(pic_list) > pic_num_max:
            error = f"图片上限{pic_num_max}张"

        if error:
            return response(msg=error, code=1)

        # 创建影集作品
        pic_id, uid, error = works.createVideoWorks(pic_list, title, label, user_id, me_id, tpl_obj, cover_id)
        if error:
            return response(msg=str(error), code=1)

        # 作品数统计
        error = works.worksStatistical(user_id)
        if error:
            raise Exception(error)

        # 历史标签表和标签表
        error = works.putVideoLabel(user_id, label)
        if error:
            raise Exception(error)

        data = {
            "pic_id": pic_id[0],
            "works_id": uid,
            "me_id": me_id
        }
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_eidtor_video_collect_works(pic_num_max=30):
    """影集作品编辑
    :param pic_num_max: 图片上限
    """
    try:

        user_id = g.user_data["user_id"]
        cover_id = request.json.get("cover_id")
        title = request.json.get("title")
        label = request.json.get("label")
        pic_list = request.json.get("pic_list")  # array [{"uid": , "title": , "label": , "pic_url": , ...}, ...]
        works_id = request.json.get("works_id")
        me_id = request.json.get("me_id")
        tpl_obj = request.json.get("tpl_obj")

        # 参数校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."
        elif not title:
            error = "Title is required."
        elif not pic_list:
            error = "PicList is required."
        elif not cover_id:
            error = "CoverId is required."
        elif not me_id:
            error = "MeId is required."
        elif not tpl_obj:
            error = "TplObj is required."

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if len(title) > constant.WORKS_TITLE_MAX:
            error = f"标题字数上限{constant.WORKS_TITLE_MAX}"
        elif len(pic_list) <= 1:
            error = "影集至少2张图片"
        elif len(pic_list) > pic_num_max:
            error = f"图片上限{pic_num_max}张"

        if error:
            return response(msg=error, code=1)

        # 编辑影集
        error = works.putVideoWorks(pic_list, title, label, cover_id, works_id, me_id, tpl_obj)
        if error:
            return response(msg=str(error), code=1)

        # 作品数减1
        error = works.putAltasWorksReduceWorksNum(works_id, user_id)
        if error:
            raise Exception(error)

        # 更新标签
        error = works.updateVideoLabel(label)
        if error:
            raise Exception(error)

        return response(data={"works_id": works_id})
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_collect_create_api_detail():
    """图集创建页面详情
    """
    try:

        user_id = g.user_data["user_id"]
        works_id = request.args.get("works_id")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."

        if error:
            return response(msg=error, code=1, status=400)

        dataList, error = works.createAltasOpionDetail(works_id)
        if error:
            raise Exception(error)

        return response(data=dataList[0] if dataList else None)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_video_collect_create_api_detail():
    """影集创建页面详情
    """
    try:

        user_id = g.user_data["user_id"]
        works_id = request.args.get("works_id")
        has_tpl_obj = request.args.get("has_tpl_obj")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."

        if error:
            return response(msg=error, code=1, status=400)

        dataList, error = works.createVideoOpionDetail(works_id)
        if error:
            raise Exception(error)
        return response(data=dataList[0] if dataList else None)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_create_article_works():
    """
    创作图文、编辑图文
    """
    try:
        # 参数

        user_id = g.user_data["user_id"]
        uid = request.json.get("uid")
        title = request.json.get("title")
        desc = request.json.get("desc")
        content = request.json.get("content")
        cover = request.json.get("cover_url")
        authorName = request.json.get("author_name")  # 对接外爬虫上传

        # 外接爬虫流程
        if request.headers.get("auth") == "wt":
            tmpUid, error = articleUploadVerify(title, content, desc, cover, authorName)
            if error is not None:
                return response(msg=error, code=1, status=400)
            return response(data=tmpUid, msg="上传成功", code=0)

        # 参数校验
        error = None
        if not user_id:
            error = "User not login"
        elif not title:
            error = "Title is required"
        elif not content:
            error = "Content is required."
        elif not isinstance(content, str):
            error = "Content type is error"
        elif not cover:
            error = "cover_url is required"

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if len(content) > constant.ARTICLE_TEXT_MAX:
            error = f"图文正文字数上限{constant.ARTICLE_TEXT_MAX}"
        elif len(title) > constant.WORKS_TITLE_MAX:
            error = f"标题字数上限{constant.WORKS_TITLE_MAX}"

        if error:
            return response(msg=error, code=1)

        cover = cover.replace(constant.DOMAIN, "")

        # 创建或修改图文
        uid, error = works.createArticleWorks(uid, title, content, user_id, desc, cover)
        if error:
            raise Exception(error)

        return response(data=uid)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_video_search_label():
    """影集搜索标签接口"""
    keyword_list = []
    try:
        # 参数
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        keyword = request.args.get("keyword")

        # 校验
        error = None
        if not keyword:
            error = "请输入关键词"
        elif len(keyword) > constant.LABEL_MAX:
            error = f"搜索字数上限{constant.LABEL_MAX}"

        if error:
            return response(msg=error, code=1)

        # 模糊查询
        cursor = client["label"].find({"label": {"$regex": keyword}, "type": "video"}, {"_id": 0, "label": 1})
        for doc in cursor:
            keyword_list.append(doc["label"])
        if keyword in keyword_list:
            keyword_list = list(set(keyword_list))
            keyword_list.remove(keyword)
            keyword_list.insert(0, keyword)
        return response(data=keyword_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_user_add_label():
    """用户添加标签"""
    try:
        # 参数
        user_id = g.user_data["user_id"]
        label = request.json.get("label")  # array

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not label:
            error = "Label is required."
        elif not isinstance(label, list):
            error = "Label must be a list. "

        if error:
            return response(msg=error, code=1, status=400)

        # 记录标签
        error = works.recordsUserLabel(label, user_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_altas_pic_sell():
    """
    图集、影集中图片上架售卖
    """
    try:

        user_id = g.user_data["user_id"]
        group = g.user_data["user_info"]["group"]
        title = request.json.get("title")
        label = request.json.get("label")
        pic_id = request.json.get("pic_id")
        format = request.json.get("format")
        pic_url = request.json.get("pic_url")
        atlas_id = request.json.get("works_id")  # 图集id
        tag = request.json.get("tag")  # 商/编
        code = request.json.get("code")  # 0代表平台定价，1代表自定义定价。
        price_item = request.json.get("price_item")  # 价格信息

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not pic_id:
            error = "PicID is required."
        elif not format:
            error = "Format is required."
        elif not pic_url:
            error = "PicUrl is required."
        elif not atlas_id:
            error = "AtlasId is required."
        elif not tag:
            error = "Tag is required."
        elif code not in [1, 0]:
            error = "Code invalid."
        elif code == 1 and not price_item:
            error = "PriceItem is required."

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if group == "comm":
            error = "只有认证摄影师才能售卖"
        elif not title:
            error = "请输入标题"
        elif len(title) > constant.WORKS_TITLE_MAX:
            error = f"标题字数上限{constant.WORKS_TITLE_MAX}"

        if error:
            return response(msg=error, code=1)

        pic_list = [{"title": title, "label": label, "pic_id": pic_id, "pic_url": pic_url, "format": format}]

        works_uid = generate_uid(24)  # 新作品id
        # 图片创作
        altas_pic_create_works_api(works_uid, user_id, title, label, pic_list)
        # 售卖信息
        pic_sell_apply(works_uid, tag, code, user_id, price_item)
        # 统计
        altas_pic_works_statisticals_api(user_id, label)

        # 图集对应图片信息修改
        doc = client["works"].find_one({"uid": atlas_id})
        temp = []
        for i in doc["pic_info"]:
            if i["pic_id"] == pic_id:
                i["title"] = title
                i["label"] = label
            temp.append(i)
        client["works"].update({"uid": atlas_id}, {"$set": {"pic_info": temp}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_spec():
    """图片规格信息接口"""
    try:
        data = [
            {"format": "S级分辨率售价", "price": float(0)},
            {"format": "M级分辨率售价", "price": float(0)},
            {"format": "L级分辨率售价", "price": float(0)},
            {"format": "扩大授权售价", "price": float(0)}
        ]
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_works_pic_list():
    """图集、影集图片列表信息接口"""
    try:

        user_id = g.user_data["user_id"]
        works_id = request.args.get("works_id")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."

        if error:
            return response(msg=error, code=1, status=400)

        doc = client["works"].find_one({"uid": works_id}, {"_id": 0, "pic_info": 1, "uid": 1})
        pic_info = doc["pic_info"]
        temp = []
        for i in pic_info:
            i["pic_url"] = constant.DOMAIN + i["pic_url"]
            temp_doc = client["pic_material"].find_one({"uid": i["pic_id"]})
            i["thumb_url"] = constant.DOMAIN + temp_doc["thumb_url"]
            i["big_pic_url"] = constant.DOMAIN + temp_doc["big_pic_url"]
            i["works_state"] = temp_doc.get("works_state") or 0
            temp.append(i)
        return response(data=temp)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_pic_resize():
    """图片压缩"""
    try:
        user_id = g.user_data["user_id"]
        urlList = request.json.get("url_list")
        temp = GenerateImage.picResize(urlList, "files", user_id, constant.DOMAIN)

        return response(data=temp)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_goods_list():
    """
    获取用户商品列表
    """
    try:

        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")
        type = request.args.get("type")  # 添加add 编辑editor
        content = request.args.get("content")  # 默认default

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询
        dataList, error = works.queryGoodsList(user_id, content, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList if dataList else [])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_user_goods_state():
    """
    删除图片商品接口
    """
    try:

        user_id = g.user_data["user_id"]
        pic_id_list = request.json.get("pic_id_list")  # array

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not pic_id_list:
            error = "PicIDList is required."
        elif not isinstance(pic_id_list, list):
            error = "The PicIDList is a list."

        if error:
            return response(msg=error, code=1, status=400)

        doc = client["goods"].update({"uid": {"$in": pic_id_list}}, {"$set": {"state": -1}}, multi=True)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_goods_detail():
    """
    购买图片详情页
    """
    try:

        user_id = g.user_data["user_id"]
        uid = request.args.get("uid")
        if not uid:
            return response(msg="Bad Request: Miss params: 'uid'.", code=1, status=400)

        # 查询数据
        data, pic_data, error = works.queryGoodsDetail(uid, user_id)
        if error:
            raise Exception(error)

        # 规格
        temp2, error = works.queryGoodsSpec(data, pic_data, user_id)
        if error:
            raise Exception(error)

        data["pic_data"] = temp2
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_material_list():
    """
    图片素材库列表
    """
    try:

        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif not content:
            error = "Content is required."

        if error:
            return response(msg=error, code=1, status=400)

        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容最多{constant.SEARCH_MAX}个字符", code=1)

        # 查询
        dataList, error = works.queryMaterialList(user_id, content, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList if dataList else [])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_material_title(length_max=32):
    """
    修改标题接口
    :param length_max: 长度上限
    """
    try:

        user_id = g.user_data["user_id"]
        pic_id = request.json.get("pic_id")
        title = request.json.get("title")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not pic_id:
            error = "PicID is required."
        elif not title:
            error = "Title is required."

        if error:
            return response(msg=error, code=1, status=400)

        if len(title) > length_max:
            return response(msg=f"标题上限{length_max}个字符", code=1)

        client["pic_material"].update({"uid": pic_id}, {"$set": {"title": title}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_material_label(length_max=20):
    """
    修改标签接口
    :param length_max: 长度上限
    """
    try:

        user_id = g.user_data["user_id"]
        pic_id = request.json.get("pic_id")
        label = request.json.get("label")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not pic_id:
            error = "PicId is required."
        elif not label:
            error = "Label is required."

        if error:
            return response(msg=error, code=1, status=400)

        if len(label) > length_max:
            return response(msg=f"标签最多选择{length_max}个", code=1)

        client["pic_material"].update({"uid": pic_id}, {"$set": {"label": label}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_material_state():
    """
    删除图片接口
    """
    try:

        user_id = g.user_data["user_id"]
        pic_id_list = request.json.get("pic_id_list")  # array

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not pic_id_list:
            error = "PicIdList is required."
        elif not isinstance(pic_id_list, list):
            error = "PicIdList is a list."

        if error:
            return response(msg=error, code=1, status=400)

        client["pic_material"].update({"uid": {"$in": pic_id_list}}, {"$set": {"state": -1}}, multi=True)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_pic_material_lib_upload():
    """素材库上传图片接口"""
    try:

        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="User not logged in.", code=1, status=400)

        # data_list = pic_upload_api(user_id)
        data_list = g.data

        # 入库
        error = works.uploadMaterialPic(data_list, user_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_audio_material_list():
    """
    音频素材库列表
    """
    try:

        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif not content:
            error = "Content is required."

        if error:
            return response(msg=error, code=1, status=400)

        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容最多{constant.SEARCH_MAX}个字符", code=1)

        pipeline = [
            {
                "$match": {
                    "user_id": user_id, "state": 1,
                    "title" if content != "default" else "null": {"$regex": content} if content != "default" else None
                }
            },
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "cover_url": {"$concat": [constant.DOMAIN, "$cover_url"]},
                    "audio_url": {"$concat": [constant.DOMAIN, "$audio_url"]}, "label": 1, "create_time": 1
                }
            }
        ]
        cursor = client["audio_material"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        return response(data=data_list if data_list else [])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_audio_material_title(length_max=32):
    """
    修改音频标题接口
    :param length_max: 长度上限
    """
    try:

        user_id = g.user_data["user_id"]
        audio_id = request.json.get("audio_id")
        title = request.json.get("title")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not audio_id:
            error = "AudioID is required."
        elif not title:
            error = "Title is required."

        if error:
            return response(msg=error, code=1, status=400)

        if len(title) > length_max:
            return response(msg=f"标题上限{length_max}个字符", code=1)

        client["audio_material"].update({"uid": audio_id}, {"$set": {"title": title}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_audio_material_label(length_max=20):
    """
    修改音频标签接口
    :param length_max: 长度上限
    """
    try:

        user_id = g.user_data["user_id"]
        audio_id = request.json.get("audio_id")
        label = request.json.get("label")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not audio_id:
            error = "AudioID is required."
        elif not label:
            error = "Label is required."

        if error:
            return response(msg=error, code=1, status=400)

        if len(label) > length_max:
            return response(msg=f"标题上限{length_max}个", code=1)

        client["audio_material"].update({"uid": audio_id}, {"$set": {"label": label}})

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_audio_material_state():
    """
    删除音频接口
    """
    try:

        user_id = g.user_data["user_id"]
        audio_id_list = request.json.get("audio_id_list")  # array

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not audio_id_list:
            error = "AudioIDList is required."
        elif not isinstance(audio_id_list, list):
            error = "PicIDList is a list."

        if error:
            return response(msg=error, code=1, status=400)

        client["audio_material"].update({"uid": {"$in": audio_id_list}}, {"$set": {"state": -1}})

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_audio_material_upload_pic(length_max=32, label_max=20):
    """
    音频库上传图片接口
    :param length_max: 长度上限
    :param label_max: 标题上限
    """
    try:

        user_id = g.user_data["user_id"]
        title = request.json.get("title")
        label = request.json.get("label")
        cover_url = request.json.get("cover_url")
        audio_url = request.json.get("audio_url")
        audio_size = request.json.get("audio_size")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not cover_url:
            error = "CoverURL is required."
        elif not audio_url:
            error = "AudioURL is required."
        elif not title:
            error = "Title is required."
        elif not audio_size:
            error = "AudioSize is required."
        elif not label:
            error = "Label is required."

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if len(title) > length_max:
            error = f"标题最长允许{length_max}个字符"
        elif len(label) > label_max:
            error = f"最多只允许选择{label_max}个标签"

        if error:
            return response(msg=error, code=1)

        uid = generate_uid(24)
        cover_url = cover_url.replace(constant.DOMAIN, "")
        audio_url = audio_url.replace(constant.DOMAIN, "")
        keyword = list(jieba.cut(title))
        condition = {
            "uid": uid, "user_id": user_id, "size": audio_size, "state": 1, "cover_url": cover_url,
            "thumb_url": cover_url, "audio_url": audio_url, "title": title, "keyword": keyword, "label": label,
            "create_time": int(time.time()) * 1000, "update_time": int(time.time()) * 1000
        }
        client["audio_material"].insert(condition)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_video_wokrs_list():
    """
    图集、影集作品列表
    """
    try:

        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")
        state = request.args.get("state")  # 0草稿，1审核中，2公开, 3违规下架，4售卖申请中，5售卖通过，6审核失败，7未公开，8全部
        type = request.args.get("type")  # tp图片，tj图集, yj影集, tw图文

        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif state not in ["0", "1", "2", "3", "4", "5", "6", "7", "8"]:
            error = "State invalid."
        elif type not in ["tp", "tj", "yj", "tw"]:
            error = "Type invalid."

        if error:
            return response(msg=error, code=1, status=400)

        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容最多{constant.SEARCH_MAX}个字符", code=1)

        # 查询
        dataList, error = works.queryAltasAndVideoList(user_id, state, content, page, num, type)
        if error:
            raise Exception(error)

        return response(data=dataList if dataList else [])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 舍弃
def get_article_wokrs_list():
    """
    图文作品列表
    """
    try:

        user_id = g.user_data["user_id"]
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")
        state = request.args.get("state")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif not content:
            error = "Content is required."
        elif state not in ["0", "1", "2", "3", "4"]:
            error = "State is invalid."

        if error:
            return response(msg=error, code=1, status=400)

        if len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容最多{constant.SEARCH_MAX}个字符", code=1)

        # 查询
        dataList, error = works.queryArticleList(user_id, content, state, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList if dataList else [])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_works_state():
    """删除作品"""
    try:

        user_id = g.user_data["user_id"]
        works_id_list = request.json.get("works_id_list")  # array

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id_list:
            error = "WorksIDList is required."
        elif not isinstance(works_id_list, list):
            error = "WorksIDList is not a list."

        if error:
            return response(msg=error, code=1, status=400)

        error = works.deleteWorks(works_id_list, user_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_works_release_apply():
    """
    作品发布审核
    """
    try:
        # 参数
        user_id = g.user_data["user_id"]
        uid = request.json.get("uid")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in"
        elif not uid:
            error = "UID is required"

        if error:
            return response(msg=error, code=1, status=400)

        user = works.getUserMobile(user_id)
        if user is None:
            error = "账号不存在"
        if user.get("mobile") is None:
            error = "请绑定手机后再发布"
        if error is not None:
            return response(msg=error, code=1)

        state, error = works.userNewWorksRelease(user_id, uid)
        if error:
            raise Exception(error)
        return response(data=state)

    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_portrait_detail():
    """
    图片作品肖像权信息详情
    """
    try:

        works_id = request.args.get("works_id")
        pic_id = request.args.get("pic_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)

        # 查询
        data, error = works.queryUserPortrait(pic_id, works_id)
        if error:
            raise Exception(error)
        return response(data=data)
    except Exception as e:
        log.error(e)


def get_pic_products_detail():
    """
    图片作品物产权信息详情
    """
    try:

        works_id = request.args.get("works_id")
        pic_id = request.args.get("pic_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)

        # 查询
        data, error = works.queryUserProduct(pic_id, works_id)
        if error:
            raise Exception(error)
        return response(data=data)
    except Exception as e:
        log.error(e)


def put_pic_portrait_editor(home_length_max=50, nick_length_max=50):
    """
    肖像权编辑接口
    :param home_length_max: 地址长度上限
    :param nick_length_max: 昵称长度上限
    """
    try:

        user_id = g.user_data["user_id"]
        works_id = request.json.get("works_id")
        pic_id = request.json.get("pic_id")
        pic_url = request.json.get("pic_url")
        shoot_addr = request.json.get("shoot_addr")
        shoot_time = request.json.get("shoot_time")
        authorizer = request.json.get("authorizer")
        b_name = request.json.get("b_name")
        b_id_card = request.json.get("b_id_card")
        b_mobile = request.json.get("b_mobile")
        b_home_addr = request.json.get("b_home_addr")
        check = IdCardAuth()

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if not pic_url:
            error = "请上传参考肖像图"
        elif not shoot_addr:
            error = "请输入拍摄地点"
        elif len(shoot_addr) > home_length_max:
            error = f"拍摄地址最多允许{home_length_max}个字符"
        elif not shoot_time:
            error = "请输入拍摄时间"
        elif not authorizer:
            error = "请输入授权人信息"
        elif not b_name:
            error = "请输入乙方姓名"
        elif len(b_name) > nick_length_max:
            error = f"乙方姓名最多允许{nick_length_max}个字符"
        elif not b_id_card:
            error = "请输入乙方身份证号"
        elif len(b_id_card) != 18:
            error = "请输入乙方正确的身份证号"
        elif not check.check_true(b_id_card):
            error = "请输入乙方正确的身份证号"
        elif not b_home_addr:
            error = "请输入乙方地址"
        elif len(b_home_addr) > constant.LENGTH_MAX:
            error = f"乙方地址长度上限{constant.LENGTH_MAX}"
        elif not b_mobile:
            error = "请输入乙方电话"

        if error:
            return response(msg=error, code=1)

        for i in authorizer:
            error = None
            if "name" not in i:
                error = "请输入授权人姓名"
            elif len(i["name"]) > nick_length_max:
                error = f"授权人姓名最多允许{nick_length_max}个字符",
            elif "id_card" not in i:
                error = "请输入授权人身份证号"
            elif len(i["id_card"]) != 18:
                error = "请输入授权人正确的身份证号"
            elif not check.check_true(i["id_card"]):
                error = "请输入授权人正确的身份证号"
            elif "sex" not in i:
                error = "请输入授权人性别"
            elif "mobile" not in i:
                error = "请输入授权人电话"
            elif len(str(i["mobile"])) != 11:
                error = "请输入正确授权人的手机号"
            elif not re.match(r"1[35678]\d{9}", str(i["mobile"])):
                error = "请输入正确授权人的手机号"
            elif "home_addre" not in i:
                error = "请输入授权人地址"
            elif len(i["home_addre"]) > constant.LENGTH_MAX:
                error = f"授权人地址长度上限{constant.LENGTH_MAX}"
            elif "is_adult" not in i:
                error = "请选择授权人是否成年"
            elif not i["is_adult"]:
                if "g_name" not in i:
                    error = "请输入监护人姓名"
                elif "g_id_card" not in i:
                    error = "请输入监护人身份证"
                elif len(i["g_id_card"]) != 18:
                    error = "请输入监护人正确的身份证号"
                elif not check.check_true(i["g_id_card"]):
                    error = "请输入监护人正确的身份证号"
                elif "g_mobile" not in i:
                    error = "请输入监护人手机"
                elif len(str(i["g_mobile"])) != 11:
                    error = "请输入监护人正确的手机号"
                elif not re.match(r"1[35678]\d{9}", str(i["g_mobile"])):
                    error = "请输入监护人正确的手机号"

            if error:
                return response(msg=error, code=1)

        pic_url = pic_url.replace(constant.DOMAIN, "")

        # 入库
        error = works.putUserPortrait(pic_url, shoot_addr, shoot_time, authorizer, b_name, b_id_card, b_mobile,
                                      b_home_addr, pic_id,
                                      works_id, user_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_property_editor(home_length_max=128, nick_length_max=50):
    """
    物产权编辑
    :param home_length_max: 地址长度上限
    :param nick_length_max: 昵称长度上限
    """
    try:

        user_id = g.user_data["user_id"]
        works_id = request.json.get("works_id")
        pic_id = request.json.get("pic_id")
        a_name = request.json.get("a_name")
        a_id_card = request.json.get("a_id_card")
        a_mobile = request.json.get("a_mobile")
        a_home_addr = request.json.get("a_home_addr")
        a_email = request.json.get("a_email")
        a_property_desc = request.json.get("a_property_desc")
        a_property_addr = request.json.get("a_property_addr")
        pic_url = request.json.get("pic_url")
        b_name = request.json.get("b_name")
        b_id_card = request.json.get("b_id_card")
        b_mobile = request.json.get("b_mobile")
        b_email = request.json.get("b_email")
        b_home_addr = request.json.get("b_home_addr")

        check = IdCardAuth()
        # rst = re.match(r"^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$",test)

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."

        if error:
            return response(msg=error, code=1, status=400)

        error = None
        if not a_name:
            error = "请输入甲方姓名"
        elif len(a_name) > nick_length_max:
            error = f"甲方姓名最多允许{nick_length_max}个字符"
        elif not a_mobile:
            error = "请输入甲方手机号"
        elif len(str(a_mobile)) != 11:
            error = "请输入正确的手机号"
        elif not re.match(r"1[35678]\d{9}", str(a_mobile)):
            error = "请输入正确的手机号"
        elif not a_email:
            error = "请输入甲方邮箱"
        elif not re.match(r"^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$", a_email):
            error = "请输入甲方正确的邮箱"
        elif not a_id_card:
            error = "请输入甲方身份证号"
        elif len(a_id_card) not in [15, 18]:
            error = "请输入甲方正确的身份证号或企业注册号"
        elif not a_home_addr:
            error = "请输入甲方地址"
        elif len(a_home_addr) > home_length_max:
            error = f"家庭地址最多允许{home_length_max}个字符"
        elif not a_property_desc:
            error = "请输入财产描述"
        elif len(a_property_desc) > constant.DESC_MAX:
            error = f"财产描述上限{constant.DESC_MAX}"
        elif not a_property_addr:
            error = "请输入财产地址"
        elif len(a_property_addr) > constant.LENGTH_MAX:
            error = f"财产地址字符上限{a_property_addr}"
        elif not pic_url:
            error = "请上传财产参考图"
        elif not b_name:
            error = "请输入乙方姓名"
        elif len(a_name) > nick_length_max:
            error = f"乙方姓名最多允许{nick_length_max}个字符"
        elif not b_id_card:
            error = "请输入乙方身份证号"
        elif len(b_id_card) not in [15, 18]:
            error = "请输入乙方正确的身份证号或企业注册号"
        elif not b_home_addr:
            error = "请输入乙方地址"
        elif len(b_home_addr) > constant.LENGTH_MAX:
            error = f"乙方地址长度上限{constant.LENGTH_MAX}"
        elif not b_email:
            error = "请输入乙方邮箱"
        elif not re.match(r"^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$", b_email):
            error = "请输入乙方正确的邮箱"
        elif len(str(b_mobile)) != 11:
            error = "请输入乙方正确的手机号"
        elif not re.match(r"1[35678]\d{9}", str(b_mobile)):
            error = "请输入乙方正确的手机号"

        if error:
            return response(msg=error, code=1)

        pic_url = pic_url.replace(constant.DOMAIN, "")
        # 入库
        error = works.putUserProduct(a_name, a_id_card, a_mobile, a_home_addr, pic_url, a_email, b_email,
                                     a_property_desc, b_name, b_id_card, b_mobile, user_id, a_property_addr, pic_id,
                                     b_home_addr, works_id)
        if error:
            raise Exception(error)
        return response(data=1)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_pic_works_sell_apply():
    """
    图片售卖申请
    """
    try:

        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        group = g.user_data["user_info"]["group"]
        if group == "comm":
            return response(msg="只有认证摄影师才能售卖", code=1)

        uid = request.json.get("works_id")
        tag = request.json.get("tag")  # 商/编
        code = request.json.get("code")  # 0代表平台定价，1代表自定义定价。
        price_item = request.json.get("price_item")  # 价格信息
        pic_id = request.json.get("pic_id")

        # 当pic存在时,说明是从图集选素材图片售卖申请并创建图片作品
        if pic_id:
            title = request.json.get("title")
            label = request.json.get("label")
            pic_list = request.json.get("pic_list")  # array [{"pic_id": , "title": , "format":, "pic_url": ,}, ...]

            if not pic_list:
                return response(msg="Bad Request: Miss param 'pic_list'.", code=1, status=400)
            wroks_uid = generate_uid(24)
            # 分词建立全文索引
            # 去除停顿词
            rst = list(jieba.cut(title, cut_all=False)) + label
            all_kw = [i for i in rst if i not in stopword]
            # 拼接字符串
            index_str = " ".join(all_kw)
            if len(pic_list) == 1:
                # 制作图片作品
                pic_title = pic_list[0]["title"]
                pic_label = pic_list[0].get("label")
                pic_id_list = [pic_list[0]["pic_id"]]  # 图片id
                pic_format = pic_list[0]["format"]
                pic_url = pic_list[0]["pic_url"].replace(constant.DOMAIN, "")
                pic_info = {
                    "pic_id": pic_id_list[0], "title": pic_title, "label": pic_label, "pic_url": pic_url,
                    "format": pic_format or "JPG"}
                number = genrate_file_number()
                keyword = list(jieba.cut(pic_title))
                # 判断该图是否已经制作过趣图作品
                doc = client["works"].find_one({"pic_id": pic_id_list[0], "state": 2, "type": "tp"})
                if doc:
                    return response(msg="请勿重复制作图片作品", code=1)
                temp_doc = client["price"].find_one({"pic_id": pic_id_list[0]})
                price_id = temp_doc["uid"]
                condition = {
                    "uid": wroks_uid, "user_id": user_id, "pic_id": pic_id_list, "type": "tp", "number": number,
                    "format": pic_format.upper(), "title": pic_title, "keyword": keyword, "label": label, "state": 0,
                    "recommend": -1, "is_portrait": False, "is_products": False, "pic_num": 1, "like_num": 0,
                    "comment_num": 0, "tag": "商", "share_num": 0, "browse_num": 0, "sale_num": 0,
                    "index_text": index_str,
                    "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000),
                    "price_id": price_id,
                    "pic_info": [pic_info]
                }
                client["works"].insert(condition)
                # 更新素材表中的状态
                client["pic_material"].update(
                    {"user_id": user_id, "uid": pic_id_list[0]}, {"$set": {"works_id": wroks_uid, "works_state": 0}}
                )
            uid = wroks_uid

        # 校验
        error = None
        if not uid:
            error = "UID is required."
        elif code not in [1, 0]:
            error = "Code invalid."
        elif tag not in ["商", "编"]:
            error = "Tag invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 更新图片作品信息
        temp_doc1 = client["portrait"].find_one({"works_id": uid, "user_id": user_id})
        temp_doc2 = client["products"].find_one({"works_id": uid, "user_id": user_id})

        condition = {
            "$set": {
                "state": 4, "tag": tag, "is_portrait": True if temp_doc1 else False,
                "is_products": True if temp_doc2 else False, "update_time": int(time.time() * 1000)
            }
        }
        client["works"].update({"uid": uid, "user_id": user_id}, condition)

        # 为S、M、L、扩大授权添加价格
        doc = client["pic_material"].find_one({"works_id": uid})
        if code == 1:
            for i in price_item:
                if len(i["format"]) == 7:
                    client["price"].update(
                        {"format": i["format"][:1], "pic_id": doc.get("uid")},
                        {"$set": {"price": i["price"], "type": code}}
                    )
                else:
                    client["price"].update(
                        {"format": "扩大授权", "pic_id": doc.get("uid")},
                        {"$set": {"price": i["price"], "type": code}}
                    )
        else:
            cursor = client["price"].find({"uid": "001"})
            for i in cursor:
                client["price"].update(
                    {"format": i.get("format"), "pic_id": doc.get("uid")},
                    {"$set": {"price": i.get("price"), "type": code}}
                )
        # 改变素材库中works_state
        client["pic_material"].update({"works_id": uid}, {"$set": {"works_state": 1}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_works_sell_info_editor():
    """
    图片售卖信息编辑
    """
    try:

        user_id = g.user_data["user_id"]
        uid = request.json.get("works_id")
        tag = request.json.get("tag")  # 商/编
        code = request.json.get("code")  # 0代表平台定价，1代表自定义定价。
        price_item = request.json.get("price_item")  # 价格信息

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not uid:
            error = "UID is required."
        elif code not in [1, 0]:
            error = "Code invalid."
        elif tag not in ["商", "编"]:
            error = "Tag invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 作品数减1
        temp2 = client["works"].find_one({"uid": uid}, {"_id": 0, "state": 1, "user_id": 1})
        if temp2 and temp2["state"] in [2, 5]:
            temp1 = client["user"].find_one({"uid": user_id}, {"_id": 0, "works_num": 1})
            if temp1["works_num"] >= 1:
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": -1}})
            else:
                client["user"].update({"uid": user_id}, {"$set": {"works_num": 0}})

        temp_doc1 = client["portrait"].find_one({"works_id": uid, "user_id": user_id})
        temp_doc2 = client["products"].find_one({"works_id": uid, "user_id": user_id})
        condition = {
            "$set": {
                "state": 0, "tag": tag, "is_portrait": True if temp_doc1 else False,
                "is_products": True if temp_doc2 else False
            }
        }
        client["works"].update({"uid": uid, "user_id": user_id}, condition)

        # 为S、M、L、扩大授权添加价格
        doc = client["pic_material"].find_one({"works_id": uid})
        if code == 1:
            for i in price_item:
                if len(i["format"]) == 7:
                    client["price"].update(
                        {"format": i["format"][:1], "pic_id": doc.get("uid")},
                        {"$set": {"price": i["price"], "type": code}}
                    )
                else:
                    client["price"].update(
                        {"format": "扩大授权", "pic_id": doc.get("uid")},
                        {"$set": {"price": i["price"]}}
                    )
        else:
            cursor = client["price"].find({"uid": "001"})
            for i in cursor:
                client["price"].update(
                    {"format": i.get("format"), "pic_id": doc.get("uid")},
                    {"$set": {"price": i.get("price"), "type": code}}
                )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_works_sell_info_detail():
    """图片售卖信息详情"""
    data = {}
    try:
        works_id = request.args.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)

        temp, type, priceItem, error = works.picSaleDetail(works_id)
        if error:
            raise Exception(error)

        data["tag"] = temp["tag"]
        data["code"] = type
        data["price_item"] = priceItem
        data["has_portrait"] = temp["is_portrait"]
        data["has_property"] = temp["is_products"]
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_area_list():
    """获取地址"""
    try:

        user_id = g.user_data["user_id"]
        step = request.args.get("step")  # 一级传1，二级传2，三级传3
        area_id = request.args.get("area_id")  # 一级默认传default, 二级、三级传对应的id

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not step:
            error = "Step is required."
        elif not area_id:
            error = "AreaId is required."

        if error:
            return response(msg=error, code=1, status=400)

        condition = {"uid": {"$regex": "0000"}}
        if step == "2":
            str_temp = area_id[:3]
            # condition = {"$and": [{"uid": {"$regex": str_temp}}, {"uid": {"$regex": "00"}}]}
            condition = {"uid": {"$regex": f"{str_temp}.00"}}
        if step == "3":
            str_temp = area_id[:4]
            condition = {"uid": {"$regex": str_temp}}
        # 查询
        cursor = client["area"].aggregate(
            [
                {"$match": condition},
                {"$project": {"_id": 0}}
            ]
        )
        data_list = [doc for doc in cursor]
        return response(data=list(filter(lambda x: x.get("uid") != area_id, data_list)))
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_share_works():
    """作品分享"""
    try:

        works_id = request.json.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)

        # 更新数据
        error = works.worksShareStatistical(works_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_download_authorized_contract():
    """下载授权合同"""
    data = {}
    try:
        doc = client["document"].find_one({"type": "authorized_contract"})
        if not doc:
            raise Exception("Lack of authorization contract")
        file_path = doc["file_path"]
        content = doc["content"]
        data["file_path"] = constant.DOMAIN + file_path
        data["content"] = content
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_agreement():
    """用户协议"""
    try:
        doc = client["document"].find_one({"type": "user_agreement"})
        if not doc:
            raise Exception("Lack of user agreement")
        content = doc["content"]
        return response(data=content)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_product_agreement():
    """物产授权"""
    try:
        doc = client["document"].find_one({"type": "product_contract"})
        if not doc:
            raise Exception("Lack of user product agreement")
        content = doc["content"]
        return response(data=content)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_portrait_agreement():
    """肖像协议"""
    try:
        doc = client["document"].find_one({"type": "portrait_agreement"})
        if not doc:
            raise Exception("Lack of user portrait agreement")
        content = doc["content"]
        return response(data=content)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_private_agreement():
    """隐私协议"""
    try:
        doc = client["document"].find_one({"type": "private_agreement"})
        if not doc:
            raise Exception("Lack of user private agreement")
        content = doc["content"]
        return response(data=content)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_works_num_statistical():
    """用户作品、素材数量统计"""
    try:
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        dynamicNum, atlasNum, videoNum, articleNum, materialNum, error = works.queryUserStaistical(user_id)
        data = {
            "article_num": articleNum,
            "material_num": materialNum,
            "dynamic_num": dynamicNum,
            "video_num": videoNum,
            "atlas_num": atlasNum
        }
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_works_release_state():
    """修改作品发布状态"""
    try:

        user_id = g.user_data["user_id"]
        works_id = request.json.get("works_id")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."

        if error:
            return response(msg=error, code=1, status=400)

        # 作品数减1
        error = works.userWorksNumSub1(works_id, user_id)
        if error:
            raise Exception(error)
        # 更新标签
        error = works.updateWorksLabelStaistical(works_id)
        if error:
            raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_comment_records():
    """添加评论"""
    try:
        # 用户是否登录
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: Please log in.", code=1, status=400)

        # 参数
        content = request.json.get("content")
        works_id = request.json.get("works_id")

        if not content:
            return response(msg="请输入内容", code=1)
        if len(content) > constant.COMMENT_MAX:
            return response(msg=f"评论字数上限{constant.COMMENT_MAX}", code=1)
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        # 评论入库
        cond, error = works.insertComment(content, user_id, works_id, g)
        if error:
            return response(msg=str(error), code=1)
        # 评论统计
        error = works.addCommentStatistical(works_id)
        if error:
            return response(msg=str(error), code=1)

        return response(cond)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def articleVideoUploadInit():
    """图文视频分片上传初始化"""
    videoUpload = upload.UploadVideo()
    videoId, chunkCount = videoUpload.videoChunkInit()
    return response(data={"video_id": videoId, "chunk_size": chunkCount})


def articleVideoUpload():
    """图文视频分片上传"""
    chunk = request.stream
    videoId = request.headers.get("videoId")
    index = request.headers.get("index")
    chunkCount = request.headers.get("chunkCount")  # 最后一次分片上传时才需要此字段

    # 参数校验
    error = None
    if not isinstance(videoId, str):
        error = "video_id invalid"
    elif not index.isdigit():
        error = "index invalid"
    if error is not None:
        return response(msg=error, code=1, status=400)

    videoUpload = upload.UploadVideo()
    chunkIndexList = videoUpload.videoChunkUpload(videoId, int(index), chunk)
    if chunkIndexList is not None:
        return response(data=chunkIndexList, msg="chunk uploaded", code=1, status=400)

    # 图文视频分片上传合并
    videoRelativePath = ""
    cover = ""
    width = 0
    height = 0
    if chunkCount:
        videoUpload = upload.UploadVideo()
        videoRelativePath = videoUpload.videoChunkMerge(videoId, int(chunkCount), "mp4")
        if videoRelativePath is None:
            return response(msg="The 'chunkCount' does not match the actual partition", code=1, status=400)
        # 视频取真
        cover, width, height = videoUpload.videoFrame(videoRelativePath)
    data = {
        "video_url": constant.DOMAIN + videoRelativePath,
        "cover_url": constant.DOMAIN + cover,
        "width": width,
        "height": height}
    return response(data=data)


def getMusicList():
    """
    获取音乐列表
    """
    category = request.json.get("category")

    # TODO 音乐分类查询
    musicList = works.getMusicList()
    return response(data=musicList)


def worksInfoAndPicfilter():
    url = request.url
    if url.endswith("user/upload/common"):  # 图片上传过滤   or url.endswith("user/local/upload")
        demo = pic.ImageFilter()
        token = request.headers.get("token")
        uid, result = verifyJWT(token)
        if not result:
            return True, None
        data, err = pic_upload_api(uid)
        g.data = data  # 后续函数所需参数
        g.error = err
        for i in data:
            rest, restMsg = demo.sendRequest("dynamic", "001", constant.DOMAIN + i["file_path"])
            if rest:
                return True, None
            else:
                return False, "图片可能涉嫌：" + restMsg
        return True, None
    elif url.endswith("works/comment"):  # 评论过滤
        data = request.get_json()
        demo = user_info.UserInfoFilter()
        rest, restMsg = demo.sendRequest("comment", "001", data.get("content"))
        if rest:
            return True, None
        else:
            return False, "评论内容可能涉嫌：" + restMsg
    return True, None


def articleUploadVerify(title, content, desc, cover, author_name):
    """对外对接爬虫接口校验"""
    if request.url.endswith("user/creation/article"):
        error = ImageUpload.paramFormatVerify(title, content, cover)
        if error:
            return "", error
        uid, user_id, error = works.spiderCreateArticleWorks(title, content, desc, cover, author_name)
        if error:
            return "", error
        # 发布申请
        works.userNewWorksRelease(user_id, uid)
        return uid, None
