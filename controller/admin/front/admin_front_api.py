# -*- coding: utf-8 -*-
"""
@Time: 2020/07/19 15:18:19
@File: admin_front_api
@Auth: money
"""
import os
import time
from urllib.parse import urlencode, parse_qs
from bson.son import SON
from flask import request
from flask import g
from middleware.auth import response
from utils.util import generate_specific_timestamp
from utils.util import generate_timestamp
from utils.util import generate_uid
from constant import constant
from controller.apps.works.app_works_api import pic_upload_api
from initialize import log
from initialize import client
from initialize import init_stamp
from dao.admin.front import front


# 微图V2.0新增
def get_search_module_show():
    """控制搜索模块是否展示"""
    try:
        doc = client["show_search_module"].find_one({"type": "banner"})
        return response(data=doc.get("state"))
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def put_search_model_show():
    """修改搜索模块状态"""
    try:
        state = request.json.get("state")
        if state not in [1, 0]:
            return response(msg="Bad Request: Params 'state' is error.", code=1, status=400)
        client["show_search_module"].update({"type": "banner"}, {"$set": {"state": state}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_banner(domain=constant.DOMAIN):
    """
    获取banner
    :param domain: 域名
    """
    try:
        # 获取数据
        pipeline = [
            {"$match": {"state": 1}},
            {"$sort": SON([("order", 1)])},
            {"$project": {
                "_id": 0, "uid": 1, "link": 1, "order": 1, "pic_url": {"$concat": [domain, "$pic_url"]},
                "create_time": {"$dateToString": {"format": "%Y-%m-%d %H:%M",
                                                  "date": {"$add": [init_stamp, "$create_time"]}}},
                "update_time": {"$dateToString": {"format": "%Y-%m-%d %H:%M",
                                                  "date": {"$add": [init_stamp, "$update_time"]}}}
            }
            }
        ]
        cursor = client["banner"].aggregate(pipeline)
        data_list = []
        i = 1
        for doc in cursor:
            doc["order"] = i
            i += 1
            link = doc.get("link")
            # 返回已选中的作品名称或用户昵称
            if link and link.find("works_id") != -1:
                title = parse_qs(link.split("?")[1])["title"][0]
            elif link and link.find("user_id") != -1:
                userId = parse_qs(link.split("?")[1])["user_id"][0]
                user = client["user"].find_one({"uid": userId}, {"_id": 0, "nick": 1})
                title = user["nick"]
            else:
                title = ""
            doc["title"] = title
            data_list.append(doc)
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 舍弃
def put_banner_link():
    """修改banner链接"""
    try:
        # 获取数据
        link = request.json.get("link")
        banner_id = request.json.get("banner_id")
        # if not link:
        #     return response(msg="Bad Request: Miss params: 'link'.", code=1, status=400)
        if not banner_id:
            return response(msg="Bad Request: Miss params: 'banner_id'", code=1, status=400)
        # 更新link
        doc = client["banner"].update({"uid": banner_id}, {"$set": {"link": link}})
        if doc == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_banner_order():
    """修改banner的序号"""
    try:
        # 获取参数
        inc = request.json.get("inc")  # 向上传1， 向下传-1
        banner_id = request.json.get("banner_id")
        if not banner_id:
            return response(msg="Bad Request: Miss params: 'banner_id'", code=1, status=400)
        # 更新
        doc = client["banner"].find_one({"uid": banner_id})
        if doc["order"] == 1 and inc == 1:
            return response()
        if doc["order"] == 10 and inc == -1:
            return response()
        doc = client["banner"].update(
            {"order": (doc["order"] - 1) if inc == 1 else (doc["order"] + 1), "state": 1},
            {"$inc": {"order": 1 if inc == 1 else -1}})
        doc = client["banner"].update({"uid": banner_id}, {"$inc": {"order": -inc}})
        if doc == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_banner_state():
    """删除banner"""
    try:
        # 获取banner_id
        banner_id = request.json.get("banner_id")
        if not banner_id:
            return response(msg="Bad Request: Miss params: 'banner_id'", code=1, status=400)
        # 更新
        doc = client["banner"].update({"uid": banner_id}, {"$set": {"state": -1}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        doc = client["banner"].find_one({"uid": banner_id})
        order = doc["order"]
        client["banner"].update({"order": {"$gt": order}, "state": 1}, {"$inc": {"order": -1}}, multi=True)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def putBannerLink():
    """
    修改链接
    """
    bannerId = request.json.get("banner_id")
    linkType = request.json.get("type")  # works user outside
    id = request.json.get("id")  # 用户id或者作品id
    link = request.json.get("link")

    # 校验
    error = None
    if bannerId is None:
        error = "banner_id is required"
    elif linkType not in ["works", "user", "outside"]:
        error = "link_tpe invalid"
    elif linkType in ["works", "user"]:
        if id is None:
            error = "id is required"
    elif linkType == "outside":
        if link is None:
            error = "outside_link is required"
    if error is not None:
        return response(msg=error, code=1, status=400)

    domain = "weitu://exp.com"

    if linkType == "works":
        doc = front.getWorks(id)
        worksType = doc.get("type")
        title = doc.get("title")
        if worksType == "tp":
            link = domain + "/PhotoDetailPage?" + urlencode(
                {"pic_id": doc.get("pic_id")[0], "works_id": id, "title": title})
        elif worksType == "tj":
            link = domain + "/AlbumDetailPage?" + urlencode(
                {"pic_id": doc.get("pic_id")[0], "works_id": id, "title": title})
        elif worksType == "yj":
            link = domain + "/YinJiDetailPage?" + urlencode({"works_id": id, "title": title})
        else:
            link = domain + "/RichDetailPage?" + urlencode({"works_id": id, "title": title})
    elif linkType == "user":
        link = domain + "/UserHomePage?" + urlencode({"user_id": id})

    front.putBannerWorksLink(bannerId, link)

    return response()


def post_upload_banner(banner_max=10):
    """
    上传banner图
    :param banner_max: banner上限
    """
    try:
        count = client["banner"].find({"state": 1}).count()
        if count >= banner_max:
            return response(msg=f"最多支持{banner_max}张轮播图片", code=1)
        user_id = g.user_data["user_id"]
        data_list, err = pic_upload_api(user_id)
        if err is not None:
            raise Exception(err)
        file_path = data_list[0]["file_path"]

        uid = generate_uid(24)
        client["banner"].insert(
            {
                "uid": uid, "order": count + 1, "state": 1, "pic_url": file_path, "link": "",
                "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_hot_keyword_list():
    """
    热搜词列表页
    :param limit: 前一日关键词热搜前10
    """
    try:
        # 获取时间戳
        now_timestamp, before_timestamp = generate_specific_timestamp()

        # 推荐关键词
        cursor = client["user_search"].find({"state": 0}, {"_id": 0, "keyword": 1})
        recomm_list = [doc["keyword"] for doc in cursor]

        hot_list = []
        if len(recomm_list) < 10:
            # 获取数据
            pipeline = [
                {"$match": {"state": 1, "$and": [{"create_time": {"$gte": before_timestamp}},
                                                 {"create_time": {"$lte": now_timestamp}}]}},
                {"$group": {"_id": {"keyword": "$keyword"}, "count": {"$sum": 1}}},
                {"$project": {"_id": 0, "keyword": "$_id.keyword", "count": 1}},
                {"$sort": SON([("count", -1)])},
                {"$limit": 10 - len(recomm_list)}
            ]
            cursor = client["user_search"].aggregate(pipeline)
            hot_list = [doc["keyword"] for doc in cursor]

        data_list = list(set(hot_list + recomm_list))
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_add_keyword():
    """添加关键词"""
    try:
        # 获取参数
        keyword = request.json.get("keyword")
        user_id = g.user_data["user_id"]
        if not keyword:
            return response(msg="Bad Request: Miss params: 'keyword'", code=1, status=400)
        # 添加
        doc = client["user_search"].find_one({"keyword": keyword, "state": 0})
        if not doc:
            client["user_search"].insert(
                {
                    "user_id": user_id, "keyword": keyword, "state": 0,
                    "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
            )
        else:
            return response(msg="关键词已存在", code=1)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_delete_keyword():
    """删除关键词"""
    try:
        # 获取参数
        keyword = request.json.get("keyword")
        if not keyword:
            return response(msg="Bad Request: Miss params: 'keyword'", code=1, status=400)
        doc = client["user_search"].update({"keyword": keyword}, {"$set": {"state": -1}}, multi=True)
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def getHotKeywordState():
    """
    热搜词模块状态
    """
    doc = client["show_search_module"].find_one({"type": "kw"}, {"_id": 0, "state": 1})
    return response(data=doc["state"])


def putHotKeywordState():
    """
    热搜词模块状态
    """
    state = request.json.get("state")  # 1展示，0关闭
    if state not in [1, 0]:
        return response(msg="state invalid", code=1, status=400)

    doc = client["show_search_module"].update({"type": "kw"}, {"$set": {"state": state}})
    return response(data=doc["state"])


def get_label_list():
    """可选栏目列表"""
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        # 查询
        pipeline = [
            {"$match": {"state": {"$in": [2, 0]}, "type": "pic"}},
            {"$sort": SON([("priority", -1), ("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "create_time": 0, "update_time": 0}}
        ]
        cursor = client["label"].aggregate(pipeline)
        data_list = []
        for d in cursor:
            d["works_num"] = client["works"].find({"label": d["label"], "state": {"$in": [2, 5]}}).count()
            data_list.append(d)
        condition = {"state": {"$in": [2, 0]}, "type": "pic"}
        count = client["label"].find(condition).count()
        data["count"] = count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_lable_priority():
    """设置标签优先级"""
    try:
        # 参数
        priority = request.json.get("priority")
        label_id = request.json.get("label_id")
        if not priority:
            return response(msg="Bad Request: Miss params: 'priority'.", code=1, status=400)
        if not label_id:
            return response(msg="Bad Request: Miss params: 'label_id'.", code=1, status=400)
        doc = client["label"].update({"uid": label_id}, {"$set": {"priority": float(priority)}})
        if doc["n"] == 0:
            return response(msg="Updated failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_show_label(option_max=20):
    """
    设置标签是显示、隐藏、删除
    :param option_max: 允许选择关键词的上限
    """
    try:
        # 参数
        keyword = request.json.get("keyword")  # array
        state = request.json.get("state")  # 显示传1，隐藏传0， 删除传-1
        if not keyword:
            return response(msg="Bad Request: Miss params: 'keyword'.", code=1, status=400)
        if len(keyword) > option_max:
            return response(msg=f"最多允许选择{option_max}个关键词", code=1)
        if state not in [-1, 0, 1]:
            return response(msg="Bad Request: Params 'state' is error.", code=1, status=400)
        doc = client["label"].update(
            {"label": {"$in": keyword}},
            {"$set": {"state": 2 if int(state) == 1 else int(state)}},
            multi=True
        )
        if doc["n"] == 0:
            return response(msg="Bad Request: Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_agreement_list():
    """文档管理"""
    try:
        cursor = client["document"].find({"state": 1}, {"_id": 0, "uid": 1, "type": 1, "content": 1})
        data_list = [doc for doc in cursor]
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_agreement_editor():
    """编辑文档"""
    try:
        # 参数
        content = request.json.get("content")
        type = request.json.get("type")
        if not type:
            return response(msg="Bad Request: Miss params: 'type'.", code=1, status=400)
        doc = client["document"].update({"type": type}, {"$set": {"content": content}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Param 'uid' is error.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def upload_docx_file():
    """上传word文件"""
    try:
        file = request.files.get("doc")
        type = request.form.get("type")
        if not type:
            return response(msg="Bad Request: Miss params: 'type'.", code=1, status=400)
        path_p = os.getcwd() + "/statics/files/document"
        file_ext = file.filename.split(".")[-1]
        if file_ext not in ["docx", "pdf", "doc"]:
            return response(msg="只允许上传word或pdf文件", code=1)
        # 创建目录
        if not os.path.exists(path_p):
            os.makedirs(path_p)
        # 写入文件
        with open(path_p + f"/{type}.{file_ext}", "wb") as f:
            f.write(file.read())
        file_path = f"/document/{type}.{file_ext}"
        doc = client["document"].update({"type": type}, {"$set": {"file_path": file_path}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Param 'uid' is error.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_top_options_list():
    """置顶作品供选列表"""
    data = {}
    try:
        # 查询条件
        sort = request.args.get("sort")  # -1倒序 1正序
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if sort not in ["1", "-1"]:
            return response(msg="Bad Request: Params 'sort' is erroe.", code=1, status=400)

        # 最近48小时
        now_timestamp, before_timestamp = generate_timestamp(days=2)

        cursor = client["top_works"].find({"state": 1})
        top_works_list = [doc["works_id"] for doc in cursor]

        # 查询条件
        pipeline = [
            {
                "$match": {
                    "uid" if top_works_list else "null": {"$nin": top_works_list} if top_works_list else None,
                    "state": {"$in": [2, 5]},
                    "type" if type else "null": {"$in": ["tp", "yj", "tj"]} if type else None,
                    "title" if content else "null": {"$regex": f"{content}"} if content else None
                }
            },
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$lookup": {
                "from": "browse_records",
                "let": {"works_id": "$uid"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$works_id", "$$works_id"]},
                                "create_time": {"$gte": before_timestamp}}},
                    {"$count": "count"}
                ],
                "as": "browse_item"}
            },
            {"$addFields": {"browse_info": {"$arrayElemAt": ["$browse_item", 0]},
                            "user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"browse_num": "$browse_info.count", "nick": "$user_info.nick"}},
            {"$sort": SON([("browse_num", int(sort))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "title": 1, "nick": 1, "browse_num": {"$ifNull": ["$browse_num", 0]}, "uid": 1}}
        ]
        cursor = client["works"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        # 总数
        pipeline = pipeline[:1]
        pipeline.append({"$count": "count"})
        cursor = client["works"].aggregate(pipeline)
        temp = [doc for doc in cursor]
        count = temp[0]["count"] if temp else 0
        data["list"] = data_list
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_top_works_list():
    """置顶作品列表"""
    try:
        cursor = client["top_works"].find({"state": 1})
        top_works_id = [doc["works_id"] for doc in cursor]
        pipeline = [
            {"$match": {"uid": {"$in": top_works_id}}},
            {"$lookup": {"from": "user", "let": {"user_id": "$user_id"},
                         "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}], "as": "user_item"}},
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick"}},
            {"$project": {"_id": 0, "uid": 1, "title": 1, "nick": 1,
                          "create_time": {"$dateToString": {"format": "%Y-%m-%d %H:%M",
                                                            "date": {"$add": [init_stamp, "$create_time"]}}}}}
        ]
        cursor = client["works"].aggregate(pipeline)
        works_list = [doc for doc in cursor]
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def post_top_works_add():
    """置顶作品添加"""
    try:
        # 参数
        works_id = request.json.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=500)
        doc = client["top_works"].find_one({"works_id": works_id, "state": 1})
        if doc:
            return response(msg="请勿重复添加", code=1)
        count = client["top_works"].find({"state": 1}).count()
        if count > 1:
            return response(msg="最多2个置顶作品", code=1)
        doc = client["works"].find_one({"uid": works_id})
        user_id = doc["user_id"]
        uid = generate_uid(24)
        client["top_works"].insert(
            {"uid": uid, "works_id": works_id, "user_id": user_id, "state": 1, "create_time": int(time.time() * 1000),
             "update_time": int(time.time() * 1000)})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def delete_recommend_top_works():
    """删除置顶作品"""
    try:
        # 参数
        uid = request.json.get("uid")
        if not uid:
            return response(msg="Bad Request: Miss params: 'uid'.", code=1, status=400)
        client["top_works"].update({"works_id": uid, "state": 1}, {"$set": {"state": -1}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_option_works_list():
    """作品列表"""
    data = {}
    try:
        # 查询条件
        sort = request.args.get("sort")  # -1倒序 1正序
        page = request.args.get("page")
        num = request.args.get("num")
        type = request.args.get("type")
        content = request.args.get("content")
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if sort not in ["1", "-1"]:
            return response(msg="Bad Request: Params 'sort' is erroe.", code=1, status=400)
        if type and type != "photo":
            return response(msg="Bad Request: Params 'type' is erroe.", code=1, status=400)
        # 最近48小时
        now_timestamp, before_timestamp = generate_timestamp(days=2)
        # 查询条件
        pipeline = [
            {
                "$match": {
                    "state": {"$in": [2, 5]},
                    "recommend" if type != "photo" else "photo_recomm": {"$ne": 1},
                    "type": {"$in": ["tp", "yj", "tj", "tw"]} if type != "photo" else {"$in": ["tp", "tj"]},
                    "title" if content else "null": {"$regex": f"{content}"} if content else None
                }
            },
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$lookup": {
                "from": "browse_records",
                "let": {"works_id": "$uid"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$works_id", "$$works_id"]},
                                "create_time": {"$gte": before_timestamp}}},
                    {"$count": "count"}
                ],
                "as": "browse_item"}
            },
            {"$addFields": {"browse_info": {"$arrayElemAt": ["$browse_item", 0]},
                            "user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"browse_num": "$browse_info.count", "nick": "$user_info.nick"}},
            {"$sort": SON([("browse_num", int(sort))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "title": 1, "nick": 1, "browse_num": {"$ifNull": ["$browse_num", 0]}, "uid": 1}}
        ]
        cursor = client["works"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        # 总数
        pipeline = pipeline[:1]
        pipeline.append({"$count": "count"})
        cursor = client["works"].aggregate(pipeline)
        temp = [doc for doc in cursor]
        count = temp[0]["count"] if temp else 0
        data["list"] = data_list
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_author_list():
    """作者列表"""
    data = {}
    try:
        # 查询条件
        sort = request.args.get("sort")  # -1倒序 1正序
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")  # nick account
        # 校验
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if sort not in ["1", "-1"]:
            return response(msg="Bad Request: Params 'sort' is erroe.", code=1, status=400)

        # 最近48小时
        now_timestamp, before_timestamp = generate_timestamp(days=2)
        # 查询条件
        pipeline = [
            {"$lookup": {
                "from": "browse_records",
                "let": {"user_id": "$uid"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]},
                                "create_time": {"$gte": before_timestamp}}},
                    {"$count": "count"}
                ],
                "as": "browse_item"}
            },
            {"$addFields": {"browse_info": {"$arrayElemAt": ["$browse_item", 0]}}},
            {"$addFields": {"browse_num": "$browse_info.count"}},
            {"$sort": SON([("browse_num", int(sort))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "follow",
                    "let": {"user_id": "$uid"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}}},
                        {"$count": "count"}
                    ],
                    "as": "follow_item"
                }
            },
            {"$addFields": {"follow_info": {"$arrayElemAt": ["$follow_item", 0]}}},
            {"$addFields": {"fans_num": "$follow_info.count"}},
            {
                "$project": {
                    "_id": 0, "nick": 1, "uid": 1,
                    "browse_num": {"$ifNull": ["$browse_num", 0]},
                    "fans_num": {"$ifNull": ["$fans_num", 0]}
                }
            }
        ]
        if content:
            cond = {
                "$match": {
                    "state": 1, "type": "user", "recommend": {"$ne": 1},
                    "$or": [{"nick": {"$regex": f"{content}"}}, {"account": {"$regex": f"{content}"}}]
                }
            }
            pipeline.insert(0, cond)
        else:
            cond = {
                "$match": {
                    "state": 1, "type": "user", "recommend": {"$ne": 1}
                }
            }
            pipeline.insert(0, cond)
        cursor = client["user"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        # 查询总数
        pipeline = pipeline[:1]
        pipeline.append({"$count": "count"})
        cursor = client["user"].aggregate(pipeline)
        temp = [doc for doc in cursor]
        count = temp[0]["count"] if temp else 0
        data["list"] = data_list
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def post_works_recommend_add():
    """推荐作品添加"""
    try:
        # 参数
        works_id_list = request.json.get("works_id_list")
        if not works_id_list:
            return response(msg="Bad Request: Miss params: 'works_id_list'.", code=1, status=400)
        for id in works_id_list:
            client["works"].update_one(
                {"uid": id},
                {"$set": {"recommend": 1, "recomm_time": int(time.time() * 1000)}}
            )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def post_author_recommend_add():
    """推荐作者添加"""
    try:
        # 参数
        author_id_list = request.json.get("author_id_list")
        if not author_id_list:
            return response(msg="Bad Request: Miss params: 'author_id_list'.", code=1, status=400)
        for id in author_id_list:
            client["user"].update_one({"uid": id}, {"$set": {"recommend": 1}})
            client["works"].update(
                {"user_id": id, "state": {"$in": [2, 5]}},
                {"$set": {"recommend": 1}},
                multi=True
            )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_recommend_author_list():
    """推荐作者列表"""
    try:
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")
        # 校验
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        pipeline = [
            {
                "$match": {
                    "type": "user", "recommend": 1, "state": 1,
                    "nick" if content else "null": content if content else None
                }
            },
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$project": {"_id": 0, "nick": 1, "uid": 1}}
        ]
        cursor = client["user"].aggregate(pipeline)
        count = client["user"].find(
            {
                "type": "user", "recommend": 1, "state": 1,
                "nick" if content else "null": content if content else None
            }
        ).count()
        return response(data={"list": list(cursor), "count": count})
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


# 微图V2.0新增
def get_recommend_works_list():
    """推荐作品列表"""
    data = {}
    try:
        page = request.args.get("page")
        num = request.args.get("num")
        content = request.args.get("content")  # nick title
        browse = request.args.get("browse")  # -1 倒序  1正序
        time = request.args.get("time")  # -1 倒序  1正序

        # 校验
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif browse not in ["-1", "1"]:
            error = "browse invalid"
        elif time not in ["-1", "1"]:
            error = "time invalid"
        if error is not None:
            return response(msg=error, code=1, status=400)

        pipeline = [
            {"$match": {"state": {"$in": [2, 5]}, "recommend": 1}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick"}},
            {
                "$match": {
                    "$or" if content else "null": \
                        [{"nick": {"$regex": f"{content}"}}, {"title": {"$regex": f"{content}"}}] if content else None
                }
            },
            {"$sort": SON([("browse_num", int(browse)), ("recomm_time", int(time))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "nick": 1, "title": 1, "label": {"$ifNull": ["$label", []]}, "browse_num": 1,
                    "recomm_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$recomm_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["works"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        data["list"] = data_list
        # 总数
        pipeline = pipeline[:5]
        pipeline.append({"$count": "count"})
        cursor = client["works"].aggregate(pipeline)
        temp = [doc for doc in cursor]
        count = temp[0]["count"] if temp else 0
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def delete_recommend_works():
    """删除推荐作品"""
    try:
        works_id_list = request.json.get("works_id_list")
        if not works_id_list:
            return response(msg="Bad Request: Miss params: 'works_id_list'", code=1, status=400)
        for id in works_id_list:
            client["works"].update_one({"uid": id}, {"$set": {"recommend": -1}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def delete_recommend_author():
    """删除推荐作者"""
    try:
        author_id_list = request.json.get("author_id_list")
        if not author_id_list:
            return response(msg="Bad Request: Miss params: 'author_id_list'", code=1, status=400)
        for id in author_id_list:
            client["user"].update_one({"uid": id}, {"$set": {"recommend": -1}})
            client["works"].update({"user_id": id, "state": {"$in": [2, 5]}, "recommend": 1},
                                   {"$set": {"recommend": -1}}, multi=True)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def post_system_recommend_rule():
    """权重排序"""
    try:
        weight = request.get_json()
        if not weight:
            return response(msg="Bad Request: Params 'weight' is error.", code=1, status=400)

        for k in weight.keys():
            client["system_rules"].update({"type": k}, {"$set": {"weight": weight[k]}})

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def post_recommend_contains_rule():
    """推荐池规则"""

    try:
        is_priority = request.json.get("is_priority")  # true false
        interval = request.json.get("interval")
        if is_priority not in [True, False]:
            return response(msg="Bad Request: Params 'is_priority' is error.", code=1, status=400)
        if not interval and interval < 0:
            return response(msg="Bad Request: Params 'interval' is error.", code=1, status=400)
        doc = client["recomm_show_rules"].find_one({})
        if not doc:
            client["recomm_show_rules"].insert(
                {
                    "is_priority": is_priority, "interval": interval, "create_time": int(time.time() * 1000),
                    "update_time": int(time.time() * 1000)
                }
            )
        else:
            client["recomm_show_rules"].update({}, {"$set": {"is_priority": is_priority, "interval": interval}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_system_recommend_info():
    """系统推荐信息"""
    try:
        cursor = client["system_rules"].find({}, {"_id": 0, "type": 1, "weight": 1})
        temp = {}
        for i in cursor:
            temp.update({i["type"]: i["weight"]})
        return response(data=temp)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_recommend_contains_info():
    """推荐池信息"""
    try:
        doc = client["recomm_show_rules"].find_one({}, {"_id": 0, "is_priority": 1, "interval": 1})
        return response(data=doc)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_photo_recommend_works_list():
    """摄影推荐作品列表"""
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        content = request.args.get("content")
        category = request.args.get("category")  # title nick
        browse = request.args.get("browse")  # -1 倒序  1正序
        time = request.args.get("time")  # -1 倒序  1正序

        # 校验
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["title", "nick"]:
            error = "category invalid"
        elif browse not in ["-1", "1"]:
            error = "browse invalid"
        elif time not in ["-1", "1"]:
            error = "time invalid"
        if error is not None:
            return response(msg=error, code=1, status=400)

        pipeline = [
            {"$match": {"photo_recomm": 1, "state": {"$in": [2, 5]}}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick"}},
            {"$sort": SON([("browse_num", int(browse)), ("recomm_photo_time", int(time))])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "nick": 1, "label": 1, "browse_num": 1,
                    "recomm_photo_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$recomm_photo_time"]}
                        }
                    }
                }
            }
        ]
        temp = pipeline[:1]
        if content:
            if category == "title":
                cond = {"$match": {"title": {"$regex": f"{content}"}}}
                pipeline.insert(1, cond)
                temp = pipeline[:2]
            else:
                cond = {"$match": {"nick": {"$regex": f"{content}"}}}
                pipeline.insert(4, cond)
                temp = pipeline[:5]
        cursor = client["works"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        # 总数
        temp.append({"$count": "count"})
        temp_cursor = client["works"].aggregate(temp)
        temp_list = [doc for doc in temp_cursor]
        count = temp_list[0]["count"] if temp_list else 0
        data["list"] = data_list
        data["count"] = count
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def post_photo_recommend_works_add():
    """摄影作品推荐添加"""
    try:
        # 参数
        works_id_list = request.json.get("works_id_list")
        if not works_id_list:
            return response(msg="Bad Request: Miss params: 'works_id_list'.", code=1, status=400)
        for id in works_id_list:
            client["works"].update_one(
                {"uid": id},
                {"$set": {"photo_recomm": 1, "recomm_photo_time": int(time.time() * 1000)}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def delete_photo_recommend_works():
    """删除推荐作品"""
    try:
        works_id_list = request.json.get("works_id_list")
        if not works_id_list:
            return response(msg="Bad Request: Miss params: 'works_id_list'", code=1, status=400)
        for id in works_id_list:
            client["works"].update_one({"uid": id}, {"$set": {"photo_recomm": -1}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def get_photo_recommend_state():
    """摄影推荐池自动添加按钮状态"""
    try:
        doc = client["show_search_module"].find_one({"type": "pic"})
        return response(data=doc.get("state"))
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 微图V2.0新增
def put_photo_recommend_state():
    """修改摄影推荐池自动添加按钮状态"""
    try:
        state = request.json.get("state")
        if state not in [1, 0]:
            return response(msg="Bad Request: Params 'state' is error.", code=1, status=400)
        client["show_search_module"].update({"type": "pic"}, {"$set": {"state": state}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def getPhotoRule():
    """
    获取摄影排序
    """
    photoRule = front.getPhotoRule()
    return response(data=photoRule)


def putPhotoRule():
    """
    修改摄影排序规则
    """
    weight = request.get_json()

    # 校验
    for k in weight.keys():
        front.putPhotoRule(k, weight[k])

    return response()
