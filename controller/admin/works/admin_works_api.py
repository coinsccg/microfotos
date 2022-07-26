# -*- coding: utf-8 -*-
"""
@Time: 2020/07/23 14:18:52
@File: admin_works_api
@Auth: money
"""
import os
import time
import datetime
from bson.son import SON
from flask import request
from middleware.auth import response
from utils.util import generate_uid
from constant import constant
from controller.apps.works.app_works_api import pic_upload_api
from controller.admin.comm import comm
from initialize import log, client, init_stamp
from dao.admin.works import material, works, music
from utils.upload_img.upload import UploadMusic

fileName = str(os.path.basename(__file__).split(".")[0])


def get_admin_pic_material_list():
    """
    图片素材列表接口
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        category = request.args.get("category")  # 标题title, 昵称传nick, 标签label
        content = request.args.get("content")

        # 校验参数
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["title", "nick", "label"]:
            error = "category invalid"
        if error:
            return response(msg=error, code=1, status=400)

        # 查询素材列表
        dataList, error = material.queryMaterialList(category, content, page, num)
        if error is not None:
            raise Exception(error)
        # 总数
        totalNum, error = material.queryMaterialTotalNum(category, content)

        data["count"] = totalNum
        data["list"] = dataList
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def put_pic_material_state():
    """
    删除图片接口
    """
    try:
        # 参数
        pic_id_list = request.json.get("pic_id_list")  # array
        if not pic_id_list:
            return response(msg="Bad Request: Miss param 'pic_id_list'.", code=1, status=400)
        doc = client["pic_material"].update({"uid": {"$in": pic_id_list}}, {"$set": {"state": -1}}, multi=True)
        if doc["n"] == 0:
            return response(msg="Bad Request: Param 'pic_id_list' is error.", code=1, status=500)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_material_detail():
    """
    图片素材详情
    """
    try:
        # 参数
        pic_id = request.args.get("pic_id")
        if not pic_id:
            return response(msg="Bad Request: Miss params: 'pic_id'.", code=1, status=400)
        # 详情
        dataList, error = material.queryMaterialDetail(pic_id)
        if error is not None:
            raise Exception(error)
        # 查询规格
        specList, error = material.queryMaterialSpec(pic_id)
        if error is not None:
            raise Exception(error)

        data = dataList[0] if dataList else {}
        if data:
            data["spec_list"] = specList
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def put_pic_material():
    """
    编辑图片素材
    """
    try:
        # 参数
        title = request.json.get("title")
        pic_id = request.json.get("pic_id")

        # 参数校验
        error = None
        if not pic_id:
            error = "pic_id is required"
        elif not title:
            error = "title is required"
        if error:
            return response(msg=error, code=1, status=400)

        if len(title) > constant.WORKS_TITLE_MAX:
            return response(msg=f"标题字数上限{constant.WORKS_TITLE_MAX}", code=1)

        error = material.putMaterial(pic_id, title)
        if error is not None:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def get_audio_material_list(domain=constant.DOMAIN):
    """
    音频素材列表接口
    :param domain: 域名
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        category = request.args.get("category")  # 标题title, 昵称传nick, 标签label
        content = request.args.get("content")
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if category not in ["title", "nick", "label"]:
            return response(msg="Bad Request: Params 'category' is error.", code=1, status=400)
        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容最长{constant.SEARCH_MAX}个字符，请重新输入", code=1)
        # 查询
        pipeline = [
            {
                "$match": {
                    "state": 1,
                    ("title" if category == "title" else "nick") if content \
                        else "null": {"$regex": content} if content else None
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
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick", "head_img_url": "$user_info.head_img_url"}},
            {"$match": {"nick" if category == "nick" else "null": {"$regex": content} if content else None}},
            {"$unset": ["user_item", "user_info"]},
            {"$sort": SON([("create_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "label": 1, "nick": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    },
                    "cover_url": {"$concat": [domain, "$cover_url"]},
                    "head_img_url": {"$concat": [domain, "$head_img_url"]},
                    "audio_url": {"$concat": [domain, "$audio_url"]}
                }
            }
        ]
        cursor = client["audio_material"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        # 统计总数用于分页
        pipeline = [
            {
                "$match": {
                    "state": 1,
                    ("title" if category == "title" else "nick") if content \
                        else "null": {"$regex": content} if content else None
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
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick", "head_img_url": "$user_info.head_img_url"}},
            {"$match": {"nick" if category == "nick" else "null": {"$regex": content} if content else None}},
            {"$count": "count"},
        ]
        cursor = client["audio_material"].aggregate(pipeline)
        count = len([doc for doc in cursor])
        data["count"] = count
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def put_audio_material_state():
    """
    删除音频接口
    """
    try:
        # 参数
        audio_id_list = request.json.get("audio_id_list")  # array
        if not audio_id_list:
            return response(msg="Bad Request: Miss param 'audio_id_list'.", code=1, status=400)
        doc = client["audio_material"].update(
            {"uid": {"$in": audio_id_list}},
            {"$set": {"state": -1}},
            multi=True
        )
        if doc["n"] == 0:
            return response(msg="Bad Request: Param 'audio_id_list' is error.", code=1, status=500)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_audio_material_detail(domain=constant.DOMAIN):
    """
    音频素材详情
    :param domain: 域名
    """
    try:
        # 参数
        audio_id = request.args.get("audio_id")
        if not audio_id:
            return response(msg="Bad Request: Miss params: 'audio_id'.", code=1, status=400)
        # 查询
        pipeline = [
            {"$match": {"uid": audio_id}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"nick": "$user_info.nick", "account": "$user_info.account"}},
            {"$unset": ["user_item", "user_info"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "label": 1, "nick": 1, "account": 1,
                    "format": 1, "size": 1, "cover_url": {"$concat": [domain, "$cover_url"]},
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    },
                    "audio_url": {"$concat": [domain, "$audio_url"]}
                }
            }
        ]
        cursor = client["audio_material"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        return response(data=data_list[0] if data_list else None)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def put_audio_material(label_length_max=20):
    """
    编辑音频素材
    :param label_length_max: 标签上限
    """
    try:
        # 参数
        title = request.json.get("title")
        label = request.json.get("label")
        audio_id = request.json.get("audio_id")
        if not audio_id:
            return response(msg="Bad Request: Miss params: 'audio_id'.", code=1, status=400)
        if not title:
            return response(msg="Bad Request: Miss params: 'title'.", code=1, status=400)
        if not label:
            return response(msg="Bad Request: Miss params: 'label'.", code=1, status=400)
        if len(title) > constant.WORKS_TITLE_MAX:
            return response(msg=f"标题允许最长{constant.WORKS_TITLE_MAX}个字符", code=1)
        if len(label) > label_length_max:
            return response(msg=f"标签最多允许{label_length_max}个", code=1)
        doc = client["audio_material"].update({"uid": audio_id}, {"$set": {"title": title, "label": label}})
        if doc["n"] == 0:
            return response(msg="Update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_audio_material_cover(domain=constant.DOMAIN):
    """
    更换音频封面接口
    :param domain: 域名
    """
    try:
        # 参数
        audio_id = request.form.get("audio_id")
        if not audio_id:
            return response(msg="Bad Request: Miss params: 'audio_id'.", code=1, status=400)
        doc = client["audio_material"].find_one({"uid": audio_id})
        if not doc:
            return response(msg="Bad Request: Params 'audio_id' if error.", code=1, status=400)
        user_id = doc.get("user_id")
        data_list = pic_upload_api(user_id)
        file_path = data_list[0]["file_path"]
        client["audio_material"].update({"uid": audio_id}, {"$set": {"cover_url": file_path}})
        cover_url = domain + file_path
        return response(data=cover_url)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_all_works_list():
    """
    图集/图文/影集作品接口
    """
    data = {}
    try:

        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        category = request.args.get("category")  # 标题title, 昵称传nick, 标签label
        state = request.args.get("state")  # 0未审核，1审核中，2公开, 3违规下架，4售卖申请中，5售卖通过，6审核失败，7未公开，8全部
        content = request.args.get("content")
        type = request.args.get("type")  # 图集传tj, 图文传tw, 影集传yj

        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        sort_way = request.args.get("sort_way")  # -1 倒序 1正序

        # 校验
        error = None
        if not num:
            error = "Num is required."
        elif not page:
            error = "Page is required."
        elif int(page) < 1 or int(num) < 1:
            error = "Page or num invalid."
        elif category not in ["title", "nick", "label"]:
            error = "Category invalid."
        elif state not in ["0", "1", "2", "3", "4", "5", "6", "7", "8"]:
            error = "State invalid."
        elif type not in ["tp", "tj", "tw", "yj"]:
            error = "Type invalid."
        elif sort_way not in ["-1", "1"]:
            error = "sort_way invalid"
        # elif not start_time:
        #     error = "start_time is required"
        # elif not end_time:
        #     error = "end_time is required"
        if error:
            return response(code=1, status=400, msg=error)

        startTime, endTime, deltaDay = comm.strDateToTimestamp(start_time, end_time)
        # if deltaDay > constant.queryDayCount:
        #     error = "查询时间范围仅限{}以内".format(constant.queryDayCount)
        # if error:
        #     return response(code=1, msg=error)

        state = int(state)

        # 查询列表
        dataList, error = works.queryWorksList(category, content, state, page, num, type, startTime, endTime, sort_way)
        if error:
            raise Exception(error)

        # 统计总数用于分页
        totalCount, err = works.queryWorksTotalNum(category, content, state, type, startTime, endTime)
        if error:
            raise Exception(error)

        data["count"] = totalCount
        data["list"] = dataList
        return response(data=data)

    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_works_state():
    """
    更改图片作品状态
    """
    try:
        # 参数
        pic_id = request.json.get('pic_id')  # array
        state = request.json.get('state')  # 删除传-1, 恢复传2, 下架传3,
        if not pic_id:
            return response(msg="Bad Request: Miss params: 'pic_id'.", code=1, status=400)
        if state not in [-1, 2, 3]:
            return response(msg="Bad Request: Param 'state' is error.", code=1, status=400)

        # 删除作品时，user中works_num -1
        cursor = client["works"].find({"uid": {"$in": pic_id}}, {"_id": 0, "user_id": 1, "state": 1})
        user_list = [doc for doc in cursor]
        for i in user_list:
            if state in [-1, 3]:
                if i["state"] in [2, 5]:
                    doc = client["user"].find_one({"uid": i["user_id"]}, {"_id": 0, "works_num": 1})
                    if doc["works_num"] >= 1:
                        client["user"].update({"uid": i["user_id"]}, {"$inc": {"works_num": -1}})
                    else:
                        client["user"].update({"uid": i["user_id"]}, {"$set": {"works_num": 0}})
            else:
                client["user"].update({"uid": i["user_id"]}, {"$inc": {"works_num": 1}})

        # 更新标签
        cursor = client["works"].find({"uid": {"$in": pic_id}})
        for doc in cursor:
            if doc["type"] in ["tp", "tj"]:

                if state in [-1, 3]:
                    if doc["state"] in [2, 5]:
                        for i in doc["label"]:
                            temp = client["label"].find_one({"label": i, "state": 2, "type": "pic"})
                            if temp:
                                if temp["works_num"] == 1:
                                    client["label"].update({"label": i, "type": "pic"},
                                                           {"$set": {"state": -1, "works_num": 0}})
                                elif temp["works_num"] > 1:
                                    client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})
                    # 下架
                    title = doc["title"]
                    msg_uid = generate_uid(16)
                    client["message"].insert(
                        {
                            "uid": msg_uid, "user_id": doc["user_id"], "push_people": "系统消息",
                            "desc": f"您的作品《{title}》因违规被下架", "state": 1, "type": 1,
                            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                        }
                    )
                else:
                    for i in doc["label"]:
                        temp = client["label"].find_one({"label": i, "type": "pic"})
                        if temp and temp["state"] == 2:
                            client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": 1}})
                        elif temp and (temp["state"] in [-1, 1]):
                            client["label"].update({"label": i, "type": "pic"},
                                                   {"$set": {"state": 2, "works_num": 1}})
                        else:
                            uid = generate_uid(16)
                            client["label"].insert(
                                {
                                    "uid": uid, "priority": float(0), "type": "pic", "label": i, "works_num": 1,
                                    "state": 2, "create_time": int(time.time() * 1000),
                                    "update_time": int(time.time() * 1000)
                                }
                            )
        if state == 2:
            for i in pic_id:
                doc = client["works"].find_one({"uid": i})
                temp_doc = client["user"].find_one({"uid": doc["user_id"]})
                if temp_doc["recommend"] == 1:
                    client["works"].update_one({"uid": i},
                                               {"$set": {"recommend": 1, "recomm_time": int(time.time() * 1000)}})
        for i in pic_id:
            doc = client["works"].find_one({"uid": i}, {"_id": 0, "type": 1})
            # 更新图片作品素材works_state
            if doc.get("type") == "tp":
                client["pic_material"].update({"works_id": i}, {"$set": {"works_state": state}})

        # 更新
        client["works"].update(
            {"uid": {"$in": pic_id}},
            {"$set": {"state": state, "create_time": int(time.time() * 1000)}},
            multi=True
        )

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_works_info():
    """
    图片编辑
    """
    try:

        works_id = request.json.get("works_id")
        title = request.json.get("title")
        label = request.json.get("label")
        state = request.json.get("state")  # 0草稿，1公开审核中，2公开， 3违规下架，4售卖申请中，5售卖,  6审核失败，7未公开
        tag = request.json.get("tag")  # 编/商

        # 校验
        error = None
        if not works_id:
            error = "WorksID is required."
        elif not title:
            error = "Title is required."
        elif state not in [0, 1, 2, 3, 4, 5, 6, 7]:
            error = "State invalid."
        elif tag not in ["商", "编"]:
            error = "Tag invalid."

        if error:
            return response(msg=error, code=1, status=400)

        if len(title) > constant.WORKS_TITLE_MAX:
            return response(msg=f"搜索字数上限{constant.WORKS_TITLE_MAX}", code=1)

        for i in label:
            if len(i) > constant.LABEL_MAX:
                return response(msg=f"标签字数上限{constant.LABEL_MAX}", code=1)

        doc = client["works"].find_one({"uid": works_id})
        if not doc:
            return response(msg="WorksID is invalid.", code=1, status=400)
        user_id = doc["user_id"]
        if state in [2, 5]:
            if doc["state"] in [2, 5]:
                for i in doc["label"]:
                    if i not in label:
                        temp = client["label"].find_one({"label": i, "state": 2, "type": "pic"})
                        if temp:
                            if temp["works_num"] == 1:
                                client["label"].update({"label": i, "type": "pic"},
                                                       {"$set": {"state": -1, "works_num": 0}})
                            elif temp["works_num"] > 1:
                                client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})
                for i in label:
                    if i not in doc["label"]:
                        temp = client["label"].find_one({"label": i, "type": "pic"})
                        if temp and temp["state"] == 2:
                            count = client["works"]. \
                                find({"label": i, "state": {"$in": [2, 5]}, "type": {"$in": ["tj", "tp"]}}).count()
                            client["label"].update({"label": i, "type": "pic"}, {"$set": {"works_num": count}})
                        elif temp and (temp["state"] in [-1, 1]):
                            client["label"].update({"label": i, "type": "pic"}, {"$set": {"works_num": 1}})
                        else:
                            uid = generate_uid(16)
                            client["label"].insert(
                                {
                                    "uid": uid, "priority": float(0), "type": "pic", "label": i, "works_num": 1,
                                    "state": 2, "create_time": int(time.time() * 1000),
                                    "update_time": int(time.time() * 1000)
                                }
                            )

            else:
                for i in label:
                    temp = client["label"].find_one({"label": i, "type": "pic"})
                    if temp and temp["state"] == 2:
                        client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": 1}})
                    elif temp and (temp["state"] in [1, -1]):
                        client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": 2, "works_num": 1}})
                    else:
                        uid = generate_uid(16)
                        client["label"].insert(
                            {
                                "uid": uid, "priority": float(0), "type": "pic", "label": i, "works_num": 1,
                                "state": 2, "create_time": int(time.time() * 1000),
                                "update_time": int(time.time() * 1000)
                            }
                        )
                # 作品数+1
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": 1}})

            temp_doc = client["user"].find_one({"uid": user_id})
            if temp_doc["recommend"] == 1:
                client["works"].update_one({"uid": works_id},
                                           {"$set": {"recommend": 1, "recomm_time": int(time.time() * 1000)}})
        else:
            if doc["state"] in [2, 5]:
                for i in doc["label"]:
                    temp = client["label"].find_one({"label": i, "state": 2, "type": "pic"})
                    if temp:
                        if temp["works_num"] == 1:
                            client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": -1, "works_num": 0}})
                        elif temp["works_num"] > 1:
                            client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})
                # 作品数-1
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": -1}})
        # 更新图片作品素材works_state
        if doc.get("type") == "tp":
            client["pic_material"].update({"works_id": works_id}, {"$set": {"works_state": state}})
            # 若state==5，直接默认平台定价
            if state == 5:
                cursor = client["price"].find({"uid": "001"})
                for i in cursor:
                    client["price"].update(
                        {"format": i.get("format"), "pic_id": doc.get("pic_id")[0]},
                        {"$set": {"price": i.get("price"), "type": 0}},
                        multi=True
                    )

        # 更新
        client["works"].update(
            {"uid": works_id},
            {"$set": {"title": title, "state": state, "label": label, "tag": tag,
                      "update_time": int(time.time() * 1000)}}
        )

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_works_audit_list(domain=constant.DOMAIN):
    """
    待审核作品列表
    :param domain: 域名
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        category = request.args.get("category")  # 标题title, 账号account
        content = request.args.get("content")
        type = request.args.get("type")  # 图片传tp， 图集传tj, 图文传tw, 影集yj, 全部传defualt

        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if category not in ["title", "account"]:
            return response(msg="Bad Request: Params 'category' is error.", code=1, status=400)
        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容最长{constant.SEARCH_MAX}个字符", code=1)
        if type not in ["tp", "tj", "tw", "default", "yj"]:
            return response(msg="Bad Request: Params 'type' is error.", code=1, status=400)
        # 查询
        pipeline = [
            {
                "$match": {
                    ("title" if category == "title" else "null") if content else \
                        "null": {"$regex": content} if content else None,
                    "type" if type != "default" else "null": \
                        ({"$in": ["tp", "tj"]} if type == "tj" else type) if type != "default" else None,
                    "state": {"$in": [1, 4]}
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
            {
                "$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}
            },
            {"$addFields": {"account": "$user_info.account", "nick": "$user_info.nick"}},
            {"$match": {"account" if category == "account" else "null": \
                            {"$regex": content} if category == "account" else None}},
            {"$sort": SON([("update_time", -1)])},
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {
                "$lookup": {
                    "from": "pic_material",
                    "let": {"pic_id": "$pic_id"},
                    "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}],
                    "as": "pic_temp_item"
                }
            },
            {
                "$addFields": {"pic_info": {"$arrayElemAt": ["$pic_item", 0]}}
            },
            {
                "$addFields": {
                    "pic_item": {
                        "$map": {
                            "input": "$pic_temp_item",
                            "as": "item",
                            "in": {
                                "big_pic_url": {"$concat": [domain, "$$item.big_pic_url"]},
                                "thumb_url": {"$concat": [domain, "$$item.thumb_url"]}
                            }
                        }
                    }
                }
            },
            {"$unset": ["user_item", "user_info", "pic_temp_item", "pic_info"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "pic_item": 1, "format": 1, "label": {"$slice": ["$label", 5]}, "state": 1,
                    "title": 1, "type": 1, "cover_url": {"$concat": [domain, "$cover_url"]}, "account": 1, "nick": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$update_time"]}
                        }
                    }
                }
            }
        ]
        temp = pipeline[:5]
        temp.append({"$count": "count"})
        cursor = client["works"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        cursor = client["works"].aggregate(temp)
        count = [doc for doc in cursor]
        data["count"] = count[0]["count"] if count else 0
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_pic_works_autio_state():
    """作品审核"""
    try:
        # 参数
        works_id = request.json.get("works_id")  # array
        state = request.json.get("state")  # 2通过 6驳回
        note = request.json.get("note")

        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        if state not in [4, 2, 6]:
            return response(msg="Bad Request: Params 'state' if error.", code=1, status=400)
        if state == 6 and not note:
            return response(msg="请输入驳回原因", code=1)

        if state == 2:
            for id in works_id:
                user_doc = client["works"].find_one({"uid": id})
                user_id = user_doc["user_id"]
                title = user_doc["title"]
                if user_doc["state"] == 1:
                    client["works"].update_one(
                        {"uid": id},
                        {"$set": {"state": 2, "update_time": int(time.time() * 1000)}}
                    )
                    # 售卖申请消息通过
                    msg_uid = generate_uid(16)
                    client["message"].insert(
                        {
                            "uid": msg_uid, "user_id": user_id, "push_people": "系统消息",
                            "desc": f"您的作品《{title}》发布申请通过", "state": 1, "type": 1,
                            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                        }
                    )
                else:
                    client["works"].update_one(
                        {"uid": id},
                        {"$set": {"state": 5, "update_time": int(time.time() * 1000)}})

                    # 已上架的商品修改价格后购物车同步价格
                    doc = client["works"].find_one({"uid": id})
                    cursor = client["price"].find({"uid": doc["price_id"]})
                    for i in cursor:
                        client["order"].update(
                            {"pic_id": i["pic_id"], "spec": i["format"]},
                            {"$set": {"price": i["price"]}}
                        )

                    # 售卖申请消息通过
                    msg_uid = generate_uid(16)
                    client["message"].insert(
                        {
                            "uid": msg_uid, "user_id": user_id, "push_people": "系统消息",
                            "desc": f"您的作品《{title}》售卖申请通过", "state": 1, "type": 1,
                            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                        }
                    )

                temp_doc = client["user"].find_one({"uid": user_id})
                if temp_doc["recommend"] == 1:
                    client["works"].update_one({"uid": id},
                                               {"$set": {"recommend": 1, "recomm_time": int(time.time() * 1000)}})

                if user_doc["type"] == "tp":
                    if user_doc["state"] == 1:
                        client["pic_material"].update({"works_id": id}, {"$set": {"works_state": 2}})
                    else:
                        client["pic_material"].update({"works_id": id}, {"$set": {"works_state": 5}})

                if user_doc["type"] in ["tj", "tp"]:
                    # 发布时统label
                    for i in user_doc["label"]:
                        # 更新标签表中works_num
                        doc = client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": 2}})
                        if doc["n"] == 0:
                            uid = generate_uid(16)
                            client["label"].insert(
                                {
                                    "uid": uid, "priority": 0.0, "type": "pic", "label": i,
                                    "works_num": 1, "state": 2, "create_time": int(time.time() * 1000),
                                    "update_time": int(time.time() * 1000)
                                }
                            )
                        else:
                            count = client["works"]. \
                                find({"label": i, "type": {"$in": ["tp", "tj"]}, "state": {"$in": [2, 5]}}).count()
                            client["label"].update({"label": i, "type": "pic"}, {"$set": {"works_num": count + 1}})
                # 如果作者被推荐，那么作品加入摄影推荐列表
                photo_doc = client["show_search_module"].find_one({"type": "pic"})
                user_temp_doc = client["user"].find_one({"uid": user_id})
                if photo_doc["state"] == 1 and user_temp_doc["group"] == "auth" and (user_doc["type"] in ["tp", "tj"]):
                    client["works"].update({"uid": id},
                                           {"$set": {"photo_recomm": 1, "recomm_photo_time": int(time.time() * 1000)}})

                # 作品数+1
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": 1}})

        # 驳回
        else:
            client["works"].update(
                {"uid": {"$in": works_id}},
                {"$set": {"state": 6, "update_time": int(time.time() * 1000)}})
            cursor = client["works"].find({"uid": {"$in": works_id}})
            for doc in cursor:
                uid = generate_uid(16)
                title = doc["title"]
                type = doc["type"]
                if type == 1:
                    desc = f"您的作品《{title}》发布申请被驳回, 原因是：{note}"
                else:
                    desc = f"您的作品《{title}》售卖申请被驳回, 原因是：{note}"
                client["message"].insert(
                    {
                        "uid": uid, "user_id": doc["user_id"], "push_people": "系统消息", "desc": desc, "state": 1,
                        "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000), "type": 1
                    }
                )

        # 更新数据
        if state == 2:
            cursor = client["works"].find({"uid": {"$in": works_id}})
            today = datetime.date.today()
            today_stamp = int(time.mktime(today.timetuple()) * 1000)
            for i in cursor:
                doc = client["user_statistical"].update(
                    {"user_id": i["user_id"], "date": today_stamp},
                    {"$inc": {"goods_num": 1}}
                )
                if doc["n"] == 0:
                    condition = {
                        "user_id": i["user_id"], "date": today_stamp, "works_num": 0, "sale_num": 0, "browse_num": 0,
                        "amount": float(0), "like_num": 0, "goods_num": 1, "register_num": 0, "comment_num": 0,
                        "share_num": 0, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                    }
                    client["user_statistical"].insert(condition)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_works_detail(domain=constant.DOMAIN):
    """
    图片作品详情
    :param domain: 域名
    """
    try:
        # 参数
        pic_id = request.args.get("pic_id")
        if not pic_id:
            return response(msg="Bad Request: Miss params: 'pic_id'.", code=1, status=400)
        pipeline = [
            {"$match": {"uid": pic_id}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {
                "$lookup": {
                    "from": "portrait",
                    "let": {"works_id": "$uid"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$works_id", "$$works_id"]}}}],
                    "as": "portrait_item"
                }
            },
            {
                "$lookup": {
                    "from": "products",
                    "let": {"works_id": "$uid"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$works_id", "$$works_id"]}}}],
                    "as": "products_item"
                }
            },
            {
                "$lookup": {
                    "from": "price", "let": {"price_id": "$price_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$uid", "$$price_id"]}}},
                        {"$project": {"_id": 0, "format": 1, "price": 1, "pic_url": {"$concat": [domain, "$pic_url"]}}}
                    ],
                    "as": "price_item"
                }
            },
            {
                "$lookup": {
                    "from": "pic_material", "let": {"pic_id": "$pic_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}},
                        {"$project": {"_id": 0, "format": 1, "big_pic_url": 1, "pic_url": 1, "size": 1}}
                    ],
                    "as": "pic_item"
                }
            },
            {
                "$addFields": {
                    "user_info": {"$arrayElemAt": ["$user_item", 0]},
                    "portrait": {"$arrayElemAt": ["$portrait_item", 0]},
                    "product": {"$arrayElemAt": ["$products_item", 0]},
                    "pic_info": {"$arrayElemAt": ["$pic_item", 0]}
                }
            },
            {
                "$addFields": {
                    "nick": "$user_info.nick", "account": "$user_info.account", "pic_url": "$pic_info.pic_url",
                    "size": "$pic_info.size", "big_pic_url": "$pic_info.big_pic_url"
                }
            },
            {"$unset": ["user_item", "user_info", "pic_item", "pic_info", "portrait._id", "product._id"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "label": {"$slice": ["$label", 5]}, "format": 1, "size": 1,
                    "nick": 1, "account": 1, "portrait": {"$ifNull": ["$portrait", "无"]},
                    "product": {"$ifNull": ["$product", "无"]}, "price_item": 1,
                    "pic_url": {"$concat": [domain, "$pic_url"]}, "tag": 1, "state": 1,
                    "big_pic_url": {"$concat": [domain, "$big_pic_url"]},
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["works"].aggregate(pipeline)
        data_list = []
        for doc in cursor:
            if doc["portrait"] != "无":
                temp = doc["portrait"]["pic_url"]
                doc["portrait"]["pic_url"] = domain + temp
            if doc["product"] != "无":
                temp1 = doc["product"]["pic_url"]
                doc["product"]["pic_url"] = domain + temp1
            data_list.append(doc)
        return response(data=data_list[0] if data_list else None)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_atals_detail(domain=constant.DOMAIN):
    """
    图集详情页
    :param domain: 域名
    """
    try:
        # 参数
        works_id = request.args.get('works_id')
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        doc = client["works"].find_one({"uid": works_id}, {"_id": 0, "type": 1})
        if doc["type"] == "tp":
            pipeline = [
                {"$match": {"uid": works_id}},
                {
                    "$lookup": {
                        "from": "user",
                        "let": {"user_id": "$user_id"},
                        "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                        "as": "user_item"
                    }
                },
                {
                    "$lookup": {
                        "from": "portrait",
                        "let": {"works_id": "$uid"},
                        "pipeline": [{"$match": {"$expr": {"$eq": ["$works_id", "$$works_id"]}}}],
                        "as": "portrait_item"
                    }
                },
                {
                    "$lookup": {
                        "from": "products",
                        "let": {"works_id": "$uid"},
                        "pipeline": [{"$match": {"$expr": {"$eq": ["$works_id", "$$works_id"]}}}],
                        "as": "products_item"
                    }
                },
                {
                    "$lookup": {
                        "from": "price", "let": {"price_id": "$price_id"},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$uid", "$$price_id"]}}},
                            {"$project": {"_id": 0, "format": 1, "price": 1,
                                          "pic_url": {"$concat": [domain, "$pic_url"]}}}
                        ],
                        "as": "price_item"
                    }
                },
                {
                    "$lookup": {
                        "from": "pic_material", "let": {"pic_id": "$pic_id"},
                        "pipeline": [
                            {"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}},
                            {"$project": {"_id": 0, "format": 1, "big_pic_url": 1, "pic_url": 1, "size": 1}}
                        ],
                        "as": "pic_item"
                    }
                },
                {
                    "$addFields": {
                        "user_info": {"$arrayElemAt": ["$user_item", 0]},
                        "portrait": {"$arrayElemAt": ["$portrait_item", 0]},
                        "product": {"$arrayElemAt": ["$products_item", 0]},
                        "pic_info": {"$arrayElemAt": ["$pic_item", 0]}
                    }
                },
                {
                    "$addFields": {
                        "nick": "$user_info.nick", "account": "$user_info.account", "pic_url": "$pic_info.pic_url",
                        "size": "$pic_info.size", "big_pic_url": "$pic_info.big_pic_url"
                    }
                },
                {"$unset": ["user_item", "user_info", "pic_item", "pic_info", "portrait._id", "products._id"]},
                {
                    "$project": {
                        "_id": 0, "uid": 1, "title": 1, "label": {"$slice": ["$label", 5]}, "format": 1, "size": 1,
                        "nick": 1, "account": 1, "portrait": {"$ifNull": ["$portrait", "无"]},
                        "product": {"$ifNull": ["$product", "无"]}, "price_item": 1,
                        "pic_url": {"$concat": [domain, "$pic_url"]}, "tag": 1, "state": 1,
                        "big_pic_url": {"$concat": [domain, "$big_pic_url"]}, "tpl_obj": 1,
                        "create_time": {
                            "$dateToString": {
                                "format": "%Y-%m-%d %H:%M",
                                "date": {"$add": [init_stamp, "$create_time"]}
                            }
                        }
                    }
                }
            ]
        else:
            pipeline = [
                {"$match": {"uid": works_id}},
                {
                    "$lookup": {
                        "from": "pic_material",
                        "let": {"pic_id": "$pic_id"},
                        "pipeline": [{"$match": {"$expr": {"$in": ["$uid", "$$pic_id"]}}}],
                        "as": "pic_temp_item"
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
                {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
                {
                    "$addFields": {
                        "pic_item": {
                            "$map": {
                                "input": "$pic_temp_item",
                                "as": "item",
                                "in": {
                                    "thumb_url": {"$concat": [domain, "$$item.thumb_url"]},
                                    "title": "$$item.title", "uid": "$$item.uid",
                                    "works_state": {"$ifNull": ["$$item.works_state", 0]}
                                }
                            }
                        },
                        "nick": "$user_info.nick", "account": "$user_info.account"
                    }
                },
                {"$unset": ["user_item", "user_info", "pic_temp_item"]},
                {
                    "$project": {
                        "_id": 0, "cover_url": {"$concat": [domain, "$cover_url"]}, "title": 1, "tpl_obj": 1,
                        "account": 1, "nick": 1, "user_id": 1, "pic_item": 1, "label": 1, "state": 1, "me_id": 1,
                        "create_time": {
                            "$dateToString": {
                                "format": "%Y-%m-%d %H:%M",
                                "date": {"$add": [init_stamp, "$create_time"]}
                            }
                        }
                    }
                }
            ]
        cursor = client["works"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        return response(data=data_list[0] if data_list else [])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_altas_deital_material_list(domain=constant.DOMAIN):
    """
    图片素材库列表接口
    :param domain: 域名
    """
    data = {}
    try:
        # 参数
        user_id = request.args.get("user_id")
        num = request.args.get("num")  # ≥1
        page = request.args.get("page")  # ≥1
        content = request.args.get("content")
        # 校验参数
        if not num:
            return response(msg="Bad Request: Miss params: 'num'.", code=1, status=400)
        if not page:
            return response(msg="Bad Request: Miss params: 'page'.", code=1, status=400)
        if int(page) < 1 or int(num) < 1:
            return response(msg="Bad Request: Params 'page' or 'num' is erroe.", code=1, status=400)
        if content and len(content) > constant.SEARCH_MAX:
            return response(msg=f"搜索内容最长{constant.SEARCH_MAX}个字符", code=1)
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        # 查询
        pipeline = [
            {"$match": {"user_id": user_id, "state": 1}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"account": "$user_info.account"}},
            {"$unset": ["user_item", "user_info"]},
            {
                "$match": {
                    "$or": [
                        {"title" if content else "null": {"$regex": content} if content else None},
                        {"label" if content else "null": content if content else None},
                        {"account" if content else "null": {"$regex": content} if content else None}
                    ]
                }
            },
            {"$skip": (int(page) - 1) * int(num)},
            {"$limit": int(num)},
            {"$sort": SON([("create_time", -1)])},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "label": 1, "account": 1,
                    "thumb_url": {"$concat": [domain, "$thumb_url"]},
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["pic_material"].aggregate(pipeline)
        data_list = [doc for doc in cursor]
        # 统计总数用于分页
        pipeline = [
            {"$match": {"user_id": user_id, "state": 1}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {"$addFields": {"account": "$user_info.account"}},
            {"$unset": ["user_item", "user_info"]},
            {
                "$match": {
                    "$or": [
                        {"title" if content else "null": {"$regex": content} if content else None},
                        {"label" if content else "null": content if content else None},
                        {"account" if content else "null": {"$regex": content} if content else None}
                    ]
                }
            },
            {"$count": "count"}
        ]
        temp_cursor = client["pic_material"].aggregate(pipeline)
        temp_data_list = [doc for doc in temp_cursor]
        data["count"] = temp_data_list[0]["count"] if temp_data_list else 0
        data["list"] = data_list if data_list else []
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_altas_works_pic_id(pic_length_max=20):
    """
    图集作品添加图片
    :param pic_length_max: 最多允许选择的图片数
    """
    try:
        # 参数
        works_id = request.json.get("works_id")
        pic_id = request.json.get("pic_id")  # array
        if not works_id:
            return response("Bad Request: Miss params 'works_id'.", code=1, status=400)
        if len(pic_id) > pic_length_max:
            return response(msg=f"最多允许选择{pic_length_max}张图片", code=1)
        doc = client["works"].find_one({"uid": works_id})
        temp_list = doc.get("pic_id") + pic_id
        doc = client["works"].update({"uid": works_id}, {"$set": {"pic_id": temp_list}})
        if doc["n"] == 0:
            return response(msg="'works' update failed.", code=1, status=400)
        return response()
    except AttributeError as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_altas_works_editor(label_length_max=20):
    """
    图集编辑作品
    :param label_length_max: 标签上限
    """
    try:

        works_id = request.json.get("works_id")
        title = request.json.get("title")
        label = request.json.get("label")
        state = request.json.get("state")  # 0未审核，1审核中，2已上架, 3违规下架

        # 校验
        error = None
        if not works_id:
            error = "WorksID is required."
        elif not title:
            error = "Title is required."
        elif state not in [0, 1, 2, 3, 4, 5, 6, 7]:
            error = "State invalid."

        if error:
            return response(msg=error, code=1, status=400)

        if label and len(label) > label_length_max:
            return response(msg=f"标签最多允许{label_length_max}个", code=1)

        if len(title) > constant.WORKS_TITLE_MAX:
            return response(msg=f"标题长度上限{constant.WORKS_TITLE_MAX}", code=1)

        for i in label:
            if len(i) > constant.LABEL_MAX:
                return response(msg=f"标签字数上限{constant.LABEL_MAX}", code=1)

        doc = client["works"].find_one({"uid": works_id})
        user_id = doc["user_id"]
        if state in [2, 5]:
            if doc["state"] in [2, 5]:
                for i in doc["label"]:
                    if i not in label:
                        temp = client["label"].find_one({"label": i, "state": 2, "type": "pic"})
                        if temp:
                            if temp["works_num"] == 1:
                                client["label"].update({"label": i, "type": "pic"},
                                                       {"$set": {"state": -1, "works_num": 0}})
                            elif temp["works_num"] > 1:
                                client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})
                for i in label:
                    if i not in doc["label"]:
                        temp = client["label"].find_one({"label": i, "type": "pic"})
                        if temp and temp["state"] == 2:
                            count = client["works"]. \
                                find({"label": i, "state": {"$in": [2, 5]}, "type": {"$in": ["tj", "tp"]}}).count()
                            client["label"].update({"label": i, "type": "pic"}, {"$set": {"works_num": count}})
                        elif temp and (temp["state"] in [-1, 1]):
                            client["label"].update({"label": i, "type": "pic"}, {"$set": {"works_num": 1}})
                        else:
                            uid = generate_uid(16)
                            client["label"].insert(
                                {
                                    "uid": uid, "priority": float(0), "type": "pic", "label": i, "works_num": 1,
                                    "state": 2, "create_time": int(time.time() * 1000),
                                    "update_time": int(time.time() * 1000)
                                }
                            )
            else:
                for i in label:
                    temp = client["label"].find_one({"label": i, "type": "pic"})
                    if temp and temp["state"] == 2:
                        client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": 1}})
                    elif temp and (temp["state"] in [-1, 1]):
                        client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": 2, "works_num": 1}})
                    else:
                        uid = generate_uid(16)
                        client["label"].insert(
                            {
                                "uid": uid, "priority": float(0), "type": "pic", "label": i, "works_num": 1,
                                "state": 2, "create_time": int(time.time() * 1000),
                                "update_time": int(time.time() * 1000)
                            }
                        )
                # 作品数+1
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": 1}})
            temp_doc = client["user"].find_one({"uid": user_id})
            if temp_doc["recommend"] == 1:
                client["works"].update_one({"uid": works_id},
                                           {"$set": {"recommend": 1, "recomm_time": int(time.time() * 1000)}})
        else:
            if doc["state"] in [2, 5]:
                for i in doc["label"]:
                    temp = client["label"].find_one({"label": i, "state": 2, "type": "pic"})
                    if temp:
                        if temp["works_num"] == 1:
                            client["label"].update({"label": i, "type": "pic"}, {"$set": {"state": -1, "works_num": 0}})
                        elif temp["works_num"] > 1:
                            client["label"].update({"label": i, "type": "pic"}, {"$inc": {"works_num": -1}})
                # 作品数-1
                client["user"].update({"uid": user_id}, {"$inc": {"works_num": -1}})
        # 更新图片作品素材works_state
        if doc.get("type") == "tp":
            client["pic_material"].update({"works_id": works_id}, {"$set": {"works_state": state}})

        # 更新
        client["works"].update(
            {"uid": works_id},
            {"$set": {"title": title, "state": state, "label": label, "update_time": int(time.time() * 1000)}}
        )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_article_works_detail(domain=constant.DOMAIN):
    """
    图文详情页
    :param domain: 域名
    """
    try:
        # 获取uid
        works_id = request.args.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        pipeline = [
            {"$match": {"uid": works_id}},
            {
                "$lookup": {
                    "from": "user",
                    "let": {"user_id": "$user_id"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$uid", "$$user_id"]}}}],
                    "as": "user_item"
                }
            },
            {"$addFields": {"user_info": {"$arrayElemAt": ["$user_item", 0]}}},
            {
                "$addFields": {
                    "nick": "$user_info.nick",
                    "head_img_url": {"$concat": [domain, "$user_info.head_img_url"]}
                }
            },
            {"$unset": ["user_item", "user_info"]},
            {
                "$project": {
                    "_id": 0, "uid": 1, "title": 1, "content": 1, "nick": 1, "head_img_url": 1, "browse_num": 1,
                    "comment_num": 1, "like_num": 1, "share_num": 1, "format": 1,
                    "create_time": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$add": [init_stamp, "$create_time"]}
                        }
                    }
                }
            }
        ]
        cursor = client["works"].aggregate(pipeline)
        data = [doc for doc in cursor]
        return response(data=data[0] if data else None)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_altas_works_pic_delete():
    """图集详情删除图片接口"""
    try:
        # 参数
        works_id = request.json.get("works_id")
        pic_id = request.json.get("pic_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        if not pic_id:
            return response(msg="Bad Request: Miss params: 'pic_id'.", code=1, status=400)
        # 更新数据库
        doc = client["works"].update({"uid": works_id}, {"$pull": {"pic_id": pic_id}})
        if doc["n"] == 0:
            return response(msg="'works' update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def postUploadMusic():
    """
    上传音频
    """
    try:
        music = request.files.get("music")
        musicUrl = UploadMusic.upload(music)
        return response(data=constant.DOMAIN + musicUrl)
    except Exception as e:
        log.error("%s.postUploadMusic() error(%s)." % (fileName, str(e)))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def postUploadMusicInfo():
    """
    上传音乐信息
    """
    title = request.json.get("title")
    category = request.json.get("category")
    musicUrl = request.json.get("music_url")
    coverUrl = request.json.get("cover_url")

    # 校验
    error = None
    if not title:
        error = "title is required"
    elif not category:
        error = "category is required"
    elif not coverUrl:
        error = "cover_url is required"
    elif not musicUrl:
        error = "music_url is required"
    if error is not None:
        return response(msg=error, code=1, status=400)

    musicUrl = musicUrl.raplace(constant.DOMAIN, "")
    coverUrl = coverUrl.raplace(constant.DOMAIN, "")
    try:
        music.insertMusicInfo(title, category, coverUrl, musicUrl)
    except Exception as e:
        log.error("music.insertMusicInfo() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response()


def putUploadMusicInfo():
    """
    修改音乐信息
    """
    uid = request.json.get("uid")
    title = request.json.get("title")
    kw = request.json.get("kw")
    musicUrl = request.json.get("music_url")
    coverUrl = request.json.get("cover_url")

    # 校验
    error = None
    if not uid:
        error = "uid is required"
    elif not title:
        error = "title is required"
    elif not kw:
        error = "kw is required"
    elif not coverUrl:
        error = "cover_url is required"
    elif not musicUrl:
        error = "music_url is required"
    if error is not None:
        return response(msg=error, code=1, status=400)

    musicUrl = musicUrl.raplace(constant.DOMAIN, "")
    coverUrl = coverUrl.raplace(constant.DOMAIN, "")
    try:
        music.updateMusicInfo(uid, title, kw, coverUrl, musicUrl)
    except Exception as e:
        log.error("music.updateMusicInfo() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response()


def putMusicRank():
    """
    修改音乐排序
    """
    uid = request.json.get("uid")
    rank = request.json.get("rank")  # 1向前移动一位， -1向后移动一位

    # 校验
    error = None
    if not uid:
        error = "uid is required"
    elif rank not in [-1, 1]:
        error = "rank invalid"
    if error is not None:
        return response(msg=error, code=1, status=400)
    try:
        music.updateMusicRank(uid, rank)
    except Exception as e:
        log.error("music.updateMusicRank() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response()


def deleteMusic():
    """
    删除音乐
    """
    uid = request.json.get("uid")

    # 校验
    if not uid:
        return response(msg="uid is required", code=1, status=400)

    try:
        music.deleteMusic(uid)
    except Exception as e:
        log.error("music.deleteMusic() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response()


def getMusicList():
    """
    获取音乐列表
    """
    kw = request.json.get("kw")
    category = request.json.get("category")
    state = request.json.get("state")  # 0未上架 1已上架 2全部
    pageNo = request.json.get("page")
    pageSize = request.json.get("num")

    # 校验
    error = None
    if not category:
        error = "category is required"
    elif state not in [0, 1, 2]:
        error = "state invalid"
    elif pageNo <= 0 and pageSize <= 0:
        error = "page or num invalid"
    if error is not None:
        return response(msg=error, code=1, status=400)

    try:
        musicList = music.getMusicList(kw, category, state, pageNo, pageSize)
    except Exception as e:
        log.error("music.getMusicList() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response(data=musicList)


def getMusicCategoryList():
    """
    获取分类列表
    """
    kw = request.json.get("kw")

    music.getMusicCategory(kw)
    try:
        categoryList = music.getMusicCategory(kw)
    except Exception as e:
        log.error("music.getMusicCategory() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response(data=categoryList)


def postMusicCategory():
    """
    添加分类
    """
    kw = request.json.get("kw")

    if not kw:
        return response(msg="kw is required", code=1, status=400)

    ct = music.getMusicCategory(kw)
    if ct:
        return response(msg="分类已经存在", code=1)

    music.insertMusicCategory(kw)
    return response()


def putMusicCategory():
    """
    编辑分类
    """
    kw = request.json.get("kw")

    if not kw:
        return response(msg="kw is required", code=1, status=400)

    ct = music.getMusicCategory(kw)
    if ct:
        return response(msg="分类已经存在", code=1)

    music.updateMusicCategory(kw)
    return response()


def deleteMusicCategory():
    """
    删除分类
    """

    kw = request.json.get("kw")

    if not kw:
        return response(msg="kw is required", code=1, status=400)

    music.deleteMusicCategory(kw)
    return response()


def getTemplateList():
    """
    模板列表
    """

    kw = request.json.get("kw")
    category = request.json.get("category")
    state = request.json.get("state")  # 0未上架 1已上架 2全部
    pageNo = request.json.get("page")
    pageSize = request.json.get("num")

    # 校验
    error = None
    if not category:
        error = "category is required"
    elif state not in [0, 1, 2]:
        error = "state invalid"
    elif pageNo <= 0 and pageSize <= 0:
        error = "page or num invalid"
    if error is not None:
        return response(msg=error, code=1, status=400)

    try:
        # TODO 根据请求参数 查询template表 可参考getMusicList()接口
        data = music.getTemplateList(kw, category, state, pageNo, pageSize)
    except Exception as e:
        log.error("music.getTemplateList() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response()


def putTemplateRank():
    """
    修改模板排序
    """
    uid = request.json.get("uid")
    rank = request.json.get("rank")  # 1向前移动一位， -1向后移动一位

    # 校验
    error = None
    if not uid:
        error = "uid is required"
    elif rank not in [-1, 1]:
        error = "rank invalid"
    if error is not None:
        return response(msg=error, code=1, status=400)
    try:
        # TODO 根据模板ID操作template表  可参考putMusicRank()接口
        music.putTemplateRank(uid, rank)
    except Exception as e:
        log.error("music.putTemplateRank() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response()


def deleteTemplate():
    """
    删除音乐
    """
    uid = request.json.get("uid")

    # 校验
    if not uid:
        return response(msg="uid is required", code=1, status=400)

    try:
        # TODO 根据模板ID操作template表  可参考deleteMusic()接口
        music.deleteTemplate(uid)
    except Exception as e:
        log.error("music.deleteTemplate() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response()


def postTemplate():
    """
    制作模板
    """
    # TODO 根据后台上传的数据更新template表


def putTemplate():
    """
    编辑模板
    """
    # TODO 根据后台上传uid和模板数据更新template表


def getTemplateCategoryList():
    """
    获取分类列表
    """
    kw = request.json.get("kw")
    try:
        categoryList = music.getTemplateCategory(kw)
    except Exception as e:
        log.error("music.getMusicCategory() error(%s)." % str(e))
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
    return response(data=categoryList)


def postTemplateCategory():
    """
    添加分类
    """
    kw = request.json.get("kw")

    if not kw:
        return response(msg="kw is required", code=1, status=400)

    ct = music.getTemplateCategoryOne(kw)
    if ct:
        return response(msg="分类已经存在", code=1)

    music.insertTemplateCategory(kw)
    return response()


def putTemplateCategory():
    """
    编辑分类
    """
    kw = request.json.get("kw")

    if not kw:
        return response(msg="kw is required", code=1, status=400)

    ct = music.getTemplateCategoryOne(kw)
    if ct:
        return response(msg="分类已经存在", code=1)

    music.updateTemplateCategory(kw)
    return response()


def deleteTemplateCategory():
    """
    删除分类
    """

    kw = request.json.get("kw")

    if not kw:
        return response(msg="kw is required", code=1, status=400)

    music.deleteMusicCategory(kw)
    return response()
