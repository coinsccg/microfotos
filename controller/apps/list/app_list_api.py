# -*- coding: utf-8 -*-
"""
@Time: 2020/07/02 09:10:59
@File: app_list_api
@Auth: money
"""
import time
import datetime
from bson.son import SON
from flask import request, g
from middleware.auth import response
from utils.util import generate_timestamp
from utils.util import generate_specific_timestamp
from constant import constant
from initialize import log, client
from dao.app.list import lists


def post_works_browse_records():
    """浏览记录"""
    try:

        user_id = g.user_data["user_id"]

        works_id = request.json.get('works_id')
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id

        # 参数校验
        if not works_id:
            return response(msg="worksID is required", code=1)
        elif len(works_id) > 32:
            return response(msg="worksID invalid", code=1)

        # 浏览+1
        error = lists.incBrowseRecords(user_id, works_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_banner():
    """
    轮播图接口
    :param domain: 域名
    """
    data = {"banner_list": [], "hot_kw": []}
    try:
        doc = client["show_search_module"].find_one({"type": "banner"})
        if doc.get("state") == 1:
            # banner
            pipeline = [
                {"$match": {"state": 1}},
                {"$sort": SON([("order", 1)])},
                # {"$limit": banner_max},
                {"$project": {"_id": 0, "pic_url": {"$concat": [constant.DOMAIN, "$pic_url"]}, "order": 1, "link": 1}}
            ]
            cursor = client["banner"].aggregate(pipeline)
            data_list = [doc for doc in cursor]
            data["banner_list"] = data_list

            # 控制热搜词版权展示
            tmp = client["show_search_module"].find_one({"type": "kw"})
            tmpList = []
            if tmp.get("state") == 1:
                # 热搜词
                now_time = datetime.datetime.now()
                last_one_time = now_time - datetime.timedelta(hours=1)

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

                hot_kw = list(set(hot_list + recomm_list))
                tmpList = hot_kw[:5]
            data["hot_kw"] = tmpList

        # 违规下架的作品超过24小时未编辑则自动删除
        _, before_timestamp = generate_timestamp(days=1)
        cursor = client["works"].find({"state": 3}, {"_id": 0, "update_time": 1, "uid": 1})

        for doc in cursor:
            if doc["update_time"] < before_timestamp:
                client["works"].update({"uid": doc["uid"]}, {"$set": {"state": -1}})

        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_label_list(label_max=5):
    """
    获取标签
    :param label_max: 栏目标签最大个数
    """
    try:
        user_id = g.user_data["user_id"]

        # 标签栏目
        # 查询条件
        doc = client["custom_label"].find_one({"user_id": user_id, "state": 1}, {"_id": 0})
        if not doc or not doc["label"]:
            pipeline = [
                {"$match": {"state": 2}},
                {"$sort": SON([("priority", -1)])},
                {"$limit": label_max},
                {"$project": {"_id": 0, "label": 1}},
            ]
            cursor = client["label"].aggregate(pipeline)
            label = [doc["label"] for doc in cursor]
        else:
            label = doc.get("label")
        return response(data=label)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error %s." % str(e), code=1, status=500)


def get_total_recomm_pool_works_priority():
    """推荐池优先作品
    """
    works_list = []
    try:
        user_id = g.user_data["user_id"]
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id

        # 获取参数
        num = request.args.get("num")
        skip_num = request.args.get("skip")
        if not all([num, skip_num]):
            return response(msg="Bad Request: Miss 'skip' or 'num'.", code=1, status=400)

        # 置顶作品
        cursor = client["top_works"].find({"state": 1}, {"_id": 0, "works_id": 1})
        works_id_list = [doc["works_id"] for doc in cursor]

        if skip_num == "0":
            if works_id_list:
                condition = {"$match": {"uid": {"$in": works_id_list}, "state": {"$in": [2, 5]}}}
                sort = {"$sort": SON([("browse_num", -1), ("like_num", -1), ("comment_num", -1), ("create_time", -1)])}
                skip = {"$skip": 0}
                top_works_list, error = lists.queryWorksList(condition, sort, user_id, skip, len(works_id_list))
                if error:
                    raise Exception(error)
                temp = []
                for i in top_works_list:
                    i["top"] = True
                    temp.append(i)
                works_list += temp
        doc = client["recomm_show_rules"].find_one({})
        is_priority = doc.get("is_priority")
        interval = doc.get("interval")
        if is_priority:
            now_timestamp, before_timestamp = generate_timestamp(hours=interval)

            # 查询条件
            condition = {
                "$match": {
                    "uid": {"$nin": works_id_list},
                    "recommend": 1, "state": {"$in": [2, 5]},
                    "$and": [
                        {"recomm_time": {"$gte": before_timestamp}},
                        {"recomm_time": {"$lte": now_timestamp}}
                    ]
                }
            }
            sort = {"$sort": SON([("recomm_time", -1)])}
            skip = {"$skip": int(skip_num)}
            recomm_works_list, error = lists.queryWorksList(condition, sort, user_id, skip, int(num))
            if error:
                raise Exception(error)
            works_list += recomm_works_list
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_total_recomm_pool_works_nopriority():
    """推荐池未优先作品
    """
    try:
        user_id = g.user_data["user_id"]
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id
        # 获取参数
        num = request.args.get("num")
        skip = request.args.get("skip")
        if not all([num, skip]):
            return response(msg="Bad Request: Miss 'skip' or 'num'.", code=1, status=400)

        doc = client["recomm_show_rules"].find_one({})
        is_priority = doc.get("is_priority")
        interval = doc.get("interval")
        _, before_timestamp = generate_timestamp(hours=interval)

        # 排除置顶作品
        cursor = client["top_works"].find({"state": 1}, {"_id": 0, "works_id": 1})
        works_id_list = [doc["works_id"] for doc in cursor]

        # 条件
        if is_priority:
            condition = {
                "$match": {
                    "uid": {"$nin": works_id_list}, "recommend": 1, "state": {"$in": [2, 5]},
                    "recomm_time": {"$lt": before_timestamp}
                }
            }
        else:
            condition = {"$match": {"uid": {"$nin": works_id_list}, "recommend": 1, "state": {"$in": [2, 5]}}}
        sort = {"$sort": SON([("browse_num", -1), ("like_num", -1), ("comment_num", -1), ("update_time", -1)])}
        skip = {"$skip": int(skip)}
        works_list, error = lists.queryWorksList(condition, sort, user_id, skip, int(num))
        if error:
            raise Exception(error)
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_total_new_norecomm_works():
    """未推荐作品中新发布作品
    """
    try:
        user_id = g.user_data["user_id"]
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id

        # 获取参数
        num = request.args.get("num")
        skip = request.args.get("skip")
        if not all([num, skip]):
            return response(msg="Bad Request: Miss 'skip' or 'num'.", code=1, status=400)

        # 一个小时以内的认定为新作品
        _, before_timestamp = generate_timestamp(hours=1)

        # 排除置顶作品
        cursor = client["top_works"].find({"state": 1}, {"_id": 0, "works_id": 1})
        works_id_list = [doc["works_id"] for doc in cursor]

        rule_cursor = client["system_rules"].find({"state": 1}, {"_id": 0, "type": 1, "weight": 1})
        rule_dict = {}
        for doc in rule_cursor:
            rule_dict.update({doc["type"]: doc["weight"]})

        # 查询条件
        condition = {
            "$match": {
                "uid": {"$nin": works_id_list}, "recommend": -1, "state": {"$in": [2, 5]},
                "update_time": {"$gte": before_timestamp}
            }
        }
        sort = {"$sort": SON([("create_time", -1), ("browse_num", -1), ("like_num", -1), ("comment_num", -1)])}
        skip = {"$skip": int(skip)}
        works_list, error = lists.queryWorksList(condition, sort, user_id, skip, int(num), is_rank=True,
                                                 rule_dict=rule_dict)
        if error:
            raise Exception(error)
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_total_old_norecomm_works():
    """未推荐作品中旧作品
    """

    try:
        user_id = g.user_data["user_id"]
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id

        # 获取参数
        num = request.args.get("num")
        skip = request.args.get("skip")
        if not all([num, skip]):
            return response(msg="Bad Request: Miss 'skip' or 'num'.", code=1, status=400)

        # 排除置顶作品
        cursor = client["top_works"].find({"state": 1}, {"_id": 0, "works_id": 1})
        works_id_list = [doc["works_id"] for doc in cursor]

        # 一个小时以内的认定为新作品
        _, before_timestamp = generate_timestamp(hours=1)

        rule_cursor = client["system_rules"].find({"state": 1}, {"_id": 0, "type": 1, "weight": 1})
        rule_dict = {}
        for doc in rule_cursor:
            rule_dict.update({doc["type"]: doc["weight"]})

        # 查询条件
        condition = {
            "$match": {
                "uid": {"$nin": works_id_list}, "recommend": -1, "state": {"$in": [2, 5]},
                "update_time": {"$lt": before_timestamp}
            }
        }
        sort = {"$sort": SON([("browse_num", -1), ("like_num", -1), ("comment_num", -1), ("create_time", -1)])}
        skip = {"$skip": int(skip)}
        works_list, error = lists.queryWorksList(condition, sort, user_id, skip, int(num), is_rank=True,
                                                 rule_dict=rule_dict)
        if error:
            raise Exception(error)
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_user_follow_author_works_list():
    """用户关注作者动态列表"""
    data = {}
    try:
        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")

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

        # 查询数据
        pipeline = [
            {"$match": {"fans_id": user_id, "state": 1}},
            {"$project": {"_id": 0, "user_id": 1, "last_look_time": 1}}
        ]
        cursor = client["follow"].aggregate(pipeline)
        user_list = []
        n = 0
        last_look_time = int(time.time() * 1000)
        for doc in cursor:
            user_list.append(doc["user_id"])
            if n == 0:
                last_look_time = doc["last_look_time"]
                n += 1
        condition = {"$match": {"user_id": {"$in": user_list}, "state": {"$in": [2, 5]}}}
        sort = {"$sort": SON([("create_time", -1)])}
        skip = {"$skip": (int(page) - 1) * int(num)}
        works_list, error = lists.queryWorksList(condition, sort, user_id, skip, num)
        if error:
            raise Exception(error)

        # 新增作品数
        count = client["works"].find(
            {"user_id": {"$in": user_list}, "create_time": {"$gte": last_look_time}}
        ).count()
        data["count"] = count
        # 更新查看时间
        doc = client["follow"].update(
            {"user_id": {"$in": user_list}, "fans_id": user_id},
            {"$set": {"last_look_time": int(time.time() * 1000)}},
            multi=True
        )
        if not doc:
            return response(msg="'last_look_time' update failed.", code=1, status=400)

        # 更新用户查看时间
        client["follow"].update(
            {"user_id": {"$in": user_list}, "fans_id": user_id},
            {"$set": {"last_look_time": int(time.time() * 1000)}}
        )

        data["works_list"] = works_list
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_random_author_list(limit=10):
    """关注列表随机作者作品
    :param limit: 用户上限
    """
    try:
        user_id = g.user_data["user_id"]
        # 查询作者
        dataList, error = lists.queryAuthorList(user_id, limit)
        user_list = [d["user_id"] for d in dataList]
        works_list = []
        for userId in user_list:
            # 查询作者作品
            condition = {"$match": {"user_id": userId, "state": {"$in": [2, 5]}}}
            sort = {"$sort": SON([("update_time", -1)])}
            skip = {"$limit": 1}
            worksOneList, error = lists.queryWorksList(condition, sort, user_id, skip, 1)
            if error:
                raise Exception(error)
            if worksOneList:
                works_list.append(worksOneList[0])
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_list():
    """
    摄影列表页
    """
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")
        label = request.args.get("label")
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id

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

        rule_cursor = client["photo_rule"].find({"state": 1}, {"_id": 0, "type": 1, "weight": 1})
        rule_dict = {}
        for doc in rule_cursor:
            rule_dict.update({doc["type"]: doc["weight"]})

        # 推荐作品
        if label == "default":
            condition = {"$match": {"photo_recomm": 1, "type": {"$in": ["tp", "tj"]}, "state": {"$in": [2, 5]}}}
            sort = {"$sort": SON([("create_time", -1)])}
            skip = {"$skip": (int(page) - 1) * int(num)}
            works_list, error = lists.queryWorksList(condition, sort, user_id, skip, int(num), is_rank=True,
                                                 rule_dict=rule_dict)
            if error:
                raise Exception(error)
        else:
            condition = {"$match": {"label": label, "type": {"$in": ["tp", "tj"]}, "state": {"$in": [2, 5]}}}
            sort = {"$sort": SON([("create_time", -1)])}
            skip = {"$skip": (int(page) - 1) * int(num)}
            works_list, error = lists.queryWorksList(condition, sort, user_id, skip, int(num), is_rank=True,
                                                 rule_dict=rule_dict)
            if error:
                raise Exception(error)
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_pic_detail():
    """
    图片、图集详情页
    """
    data = {}
    try:
        # 用户uid
        user_id = g.user_data["user_id"]
        # 获取图片uid
        works_id = request.args.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)

        # 详情数据
        pic_obj, error = lists.queryAltasDetail(works_id, user_id)
        if error:
            raise Exception(error)

        # 粉丝数
        fansNum, error = lists.queryAuthorFansNum(pic_obj["user_id"])
        if error:
            raise Exception(error)

        pic_obj["fans_num"] = fansNum

        # 浏览+1
        error = lists.incBrowseRecords(user_id, works_id)
        if error:
            raise Exception(error)

        # 查询评论
        comment_list, error = lists.query2CommentList(works_id, user_id)
        if error:
            raise Exception(error)
        pic_obj["comment_list"] = comment_list
        data["pic_data"] = pic_obj
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_video_detail():
    """
    影集详情页
    """
    try:

        user_id = g.user_data["user_id"]
        uid = request.args.get("works_id")
        if not uid:
            return response(msg="Bad Request: Miss params: 'uid'.", code=1, status=400)

        # 影集详情
        temp, error = lists.queryVideoDetail(uid, user_id)
        if error:
            raise Exception(error)

        # 浏览+1
        error = lists.incBrowseRecords(user_id, uid)
        if error:
            raise Exception(error)

        # 查询评论
        comment_list, error = lists.query2CommentList(uid, user_id)
        if error:
            raise Exception(error)
        temp["comment_list"] = comment_list

        # 粉丝数
        fansNum, error = lists.queryAuthorFansNum(temp["user_id"])
        if error:
            raise Exception(error)
        temp["fans_num"] = fansNum

        return response(data=temp)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_article_detail():
    """
    图文详情页
    """
    try:

        user_id = g.user_data["user_id"]
        uid = request.args.get("uid")

        if not uid:
            return response(msg="Bad Request: Miss params: 'uid'.", code=1, status=400)

        # 图文详情
        temp, error = lists.queryArticleDetail(uid, user_id)
        if error:
            raise Exception(error)

        # 浏览+1
        error = lists.incBrowseRecords(user_id, uid)
        if error:
            raise Exception(error)

        # 查询评论
        comment_list, error = lists.query2CommentList(uid, user_id)
        if error:
            raise Exception(error)
        temp["comment_list"] = comment_list

        # 粉丝数
        fansNum, error = lists.queryAuthorFansNum(temp["user_id"])
        if error:
            raise Exception(error)

        temp["fans_num"] = fansNum
        return response(data=temp)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_hot_keyword():
    """
    热搜关键词
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


def get_search_works():
    """
    搜索作品
    """
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")
        keyword = request.args.get("keyword")
        filter_field = request.args.get("filter_field")  # time发布时间，like_num点赞数，default默认
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id

        # 校验
        if not keyword:
            return response(data=[])

        error = None
        if not user_id:
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif not filter_field:
            error = "FilterField is required."

        if error:
            return response(msg=error, code=1, status=400)

        if len(keyword) > constant.SEARCH_MAX:
            return response(msg=f"搜索字数上限{keyword}", code=1)

        # 限制用户搜索次数
        # 1小时之内100次
        _, before_timestamp = generate_timestamp(hours=1)
        count = client["user_search"].find({"create_time": {"$gte": before_timestamp}}).count()
        if count > 100:
            return response(msg="搜索过于频繁，请稍后再试", code=1)

        # 24小时内200次
        _, before_timestamp = generate_timestamp(days=1)
        count = client["user_search"].find({"create_time": {"$gte": before_timestamp}}).count()
        if count > 200:
            return response(msg="搜索过于频繁，请稍后再试", code=1)

        # 查询话题
        condition = {
            "$match": {
                "$or": [
                    {"title": {"$regex": f"{keyword}"}},
                    {"label": {"$regex": f"{keyword}"}}
                ],
                "state": {"$in": [2, 5]}
            }
        }
        sort = {"$sort": SON([("browse_num", -1) if filter_field == "default" else \
                                  (("create_time", -1) if filter_field == "time" else ("like_num", -1))])
                }
        skip = {"$skip": (int(page) - 1) * int(num)}
        works_list, error = lists.queryWorksList(condition, sort, user_id, skip, num)
        if error:
            raise Exception(error)
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_search_author():
    """搜索作者
    """
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")
        keyword = request.args.get("keyword")
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id

        # 校验
        if not keyword:
            return response(data=[])

        error = None
        if not user_id:
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."

        if error:
            return response(msg=error, code=1, status=400)

        if len(keyword) > constant.SEARCH_MAX:
            return response(msg=f"搜索字数上限{constant.SEARCH_MAX}", code=1)

        # 查询作者
        dataList, error = lists.querySearchAuthorList(user_id, keyword)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def get_search_keyword(kw_max=30):
    """
    关键词搜索接口
    :param kw_max: 关键词上限
    """
    try:
        # 用户uid
        user_id = g.user_data["user_id"]
        keyword = request.args.get("keyword")

        # 校验
        if not keyword:
            return response(msg="请输入关键词", code=1)

        if len(keyword) > constant.SEARCH_MAX:
            return response(msg=f"搜索字数上限{constant.SEARCH_MAX}", code=1)

        # 统计用户搜索关键词
        client["user_search"].insert_one(
            {"user_id": user_id, "keyword": keyword, "create_time": int(time.time() * 1000),
             "update_time": int(time.time() * 1000), "state": 1})

        # 模糊查询
        pipeline = [
            {"$match": {"keyword": {"$regex": f"{keyword}"}, "state": 1}},
            {"$group": {"_id": "$keyword", "count": {"$sum": 1}}},
            {"$sort": SON([("count", -1)])},
            {"$limit": kw_max},
            {"$project": {"_id": 0, "keyword": "$_id"}}
        ]
        cursor = client["user_search"].aggregate(pipeline)
        data_list = [doc["keyword"] for doc in cursor]
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_works_like():
    """作品点赞接口"""
    try:
        # 用户uid
        user_id = g.user_data["user_id"]
        works_id = request.json.get("works_id", None)

        # 参数校验
        error = None
        if not user_id:
            error = "UserID is required."
        elif not works_id:
            error = "WorksID is required."
        if error:
            return response(msg=error, code=1, status=400)

        # 点赞量加减
        temp, error = lists.likeWorksChangeNum(user_id, works_id)
        if error:
            raise Exception(error)

        # 点赞统计
        error = lists.likeWorksStatistical(works_id, temp)
        if error:
            raise Exception(error)

        # 记录点赞记录
        error = lists.likeWorksRecords(user_id, works_id)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_comment_list():
    """
    评论列表页
    :param domain: 域名
    """
    try:

        user_id = g.user_data["user_id"]
        num = request.args.get("num")
        page = request.args.get("page")
        works_id = request.args.get("works_id")

        # 校验
        error = None
        if not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif not works_id:
            error = "WorksID is required."

        if error:
            return response(msg=error, code=1, status=400)

        # 查询数据
        dataList, error = lists.queryCommentList(user_id, works_id, page, num)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_comment_like():
    """评论点赞"""
    try:
        # 用户是否登录
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: Please log in.", code=1, status=400)
        works_id = request.json.get("works_id", None)
        comment_id = request.json.get("comment_id", None)
        if not comment_id:
            return response(msg="Bad Request: Miss params: 'comment_id'.", code=1, status=400)
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        # 写入点赞记录表
        n, error = lists.insertLikeComment(user_id, works_id, comment_id)
        if error:
            raise Exception(error)
        # comment表点赞量+-1
        error = lists.likeCommentNum(comment_id, n)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_delete_comment():
    """删除评论"""
    try:
        # 用户是否登录
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: Please log in.", code=1, status=400)
        comment_id = request.json.get("comment_id", None)
        if not comment_id:
            return response(msg="Bad Request: Miss params: 'comment_id'.", code=1, status=400)
        # 将state改为-1
        doc = client["comment"].update({"uid": comment_id}, {"$set": {"state": -1}})
        if doc["n"] == 0:
            return response(msg="Bad Request: Params 'comment_id' is error.", code=1, status=400)
        # 更新works中的comment_num
        doc = client["comment"].find_one({"uid": comment_id})
        works_id = doc["works_id"]
        doc = client["works"].update({"uid": works_id}, {"$inc": {"comment_num": -1}})
        if doc["n"] == 0:
            return response(msg="'works' update failed.", code=1, status=400)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_comment_report():
    """评论举报"""
    try:

        user_id = g.user_data["user_id"]
        comment_id = request.json.get("comment_id")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not comment_id:
            error = "CommentID is required."

        if error:
            return response(msg=error, code=1, status=400)

        doc = client["comment_report"].find_one({"user_id": user_id, "comment_id": comment_id, "state": 1})
        if doc:
            return response(msg="请勿重复举报", code=1)
        client["comment_report"].insert(
            {
                "comment_id": comment_id, "user_id": user_id, "state": 1,
                "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
            }
        )
        # comment表state更改为0
        # client["comment"].update({"uid": comment_id}, {"$set": {"state": 0}})
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_option_label(label_max=40):
    """
    自定义供选标签
    :param label_max: 供选择的标签上限
    """
    try:
        # 参数
        type = request.args.get("type")

        # 校验
        if type not in ["pic", "video"]:
            return response(msg="Type invalid.", code=1, status=400)

        # 查询数据库
        cursor = client["label"].aggregate(
            [
                {"$match": {"state": 2, "type": {"$in": ["pic", "video"]}}},
                {"$sample": {"size": label_max}},
                {"$project": {"_id": 0, "label": 1}}
            ]
        )
        data_list = [doc["label"] for doc in cursor]
        return response(data=data_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_custom_label(label_max=12):
    """
    自定义标签
    :param label_max: 自定义标签上限
    """
    try:
        # 用户uid
        user_id = g.user_data["user_id"]
        # 参数
        label_list = request.json.get("label_list")
        visitor_id = request.headers.get("user_id")
        user_id = user_id if user_id else visitor_id
        # 校验
        if not user_id:
            return response(msg="Bad Request: Miss params: 'user_id'.", code=1, status=400)
        if len(label_list) > label_max:
            return response(msg=f"标签上限{label_max}个", code=1)

        for i in label_list:
            if len(i) > constant.LABEL_MAX:
                return response(f"标签字数上限{constant.LABEL_MAX}", code=1)

        # 入库
        doc = client["custom_label"].find_one({"user_id": user_id, "type": "pic", "state": 1})
        if not doc:
            client["custom_label"].insert(
                {
                    "user_id": user_id, "type": "pic", "label": label_list, "state": 1,
                    "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
            )
        else:
            client["custom_label"].update(
                {"user_id": user_id, "type": "pic", "state": 1},
                {"$set": {"label": label_list, "update_time": int(time.time() * 1000)}}
            )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_follow_user():
    """作者关注接口"""
    try:
        # 用户是否登录
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: Please log in.", code=1, status=400)
        # 作者uid
        author_id = request.json.get("author_id")
        if not author_id:
            return response(msg="Bad Request: Miss params: 'author_id'.", code=1, status=400)
        doc = client["follow"].find_one({"user_id": author_id, "fans_id": user_id})
        if doc:
            if doc["state"] == 1:
                # 取消关注
                client["follow"].update({"user_id": author_id, "fans_id": user_id}, {"$set": {"state": 0}})
            else:
                # 重新关注
                timeTmp = int(time.time() * 1000)
                client["follow"].update({"user_id": author_id, "fans_id": user_id},
                                        {"$set": {"state": 1, "last_look_time": timeTmp,
                                                  "create_time": timeTmp, "update_time": timeTmp}})
        else:
            # 新增关注
            timeTmp = int(time.time() * 1000)
            condition = {
                "user_id": author_id, "fans_id": user_id, "state": 1, "last_look_time": timeTmp,
                "create_time": timeTmp, "update_time": timeTmp
            }
            client["follow"].insert(condition)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_blacklist():
    """拉黑用户或作品"""
    try:
        # 参数
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)
        black_id = request.json.get("black_id")  # 被拉黑用户id或作品id
        type = request.json.get("type")  # user用户, works作品
        if not black_id:
            return response(msg="Bad Request: Miss params: 'black_id'.", code=1, status=400)
        if not type:
            return response(msg="Bad Request: Miss params: 'type'.", code=1, status=400)
        doc = client["blacklist"].update(
            {"user_id": user_id, "black_id": black_id},
            {"$set": {"state": 1, "update_time": int(time.time() * 1000)}}
        )
        if doc["n"] == 0:
            client["blacklist"].insert(
                {
                    "user_id": user_id, "black_id": black_id, "state": 1, "update_time": int(time.time()),
                    "create_time": int(time.time() * 1000)
                }
            )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_report_works():
    """举报作品接口"""
    try:
        works_id = request.json.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        doc = client["works"].find_one({"uid": works_id})
        if not doc:
            return response(msg="Bad Request: Params 'works_id' is error.", code=1, status=400)
        type = doc["type"]
        user_id = doc["user_id"]
        doc = client["works_report"].find_one({"works_id": works_id, "state": 1})
        if not doc:
            client["works_report"].insert(
                {
                    "works_id": works_id, "state": 1, "user_id": user_id, "type": type,
                    "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
                }
            )
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_share_recommend_works_list(num=10):
    """分享页作品推荐
    :param num: 10个分享作品
    
    """
    try:
        user_id = g.user_data["user_id"]

        works_id = request.args.get("works_id")
        if not works_id:
            return response(msg="Bad Request: Miss params: 'works_id'.", code=1, status=400)
        doc = client["works"].find_one({"uid": works_id})
        if not doc:
            return response(msg="this works not exist", code=1, status=400)
        type = doc["type"]
        author_id = doc["user_id"]
        # 查询条件
        condition = {"$match": {"type": type, "user_id": author_id, "uid": {"$ne": works_id}, "state": {"$in": [2, 5]}}}
        sort = {"$sort": SON([("create_time", -1)])}
        skip = {"$skip": 0}
        works_list, error = lists.queryWorksList(condition, sort, user_id, skip, num)
        if error:
            raise Exception(error)
        temp = [doc["uid"] for doc in works_list]
        temp.append(works_id)
        # 不满足10条时采用后台推荐作品
        if len(works_list) < 10:
            author_cursor = client["recomme_author"].find({"state": 1}, {"_id": 0, "user_id": 1}).limit(11)
            recomm_author = [doc["user_id"] for doc in author_cursor]
            if recomm_author:
                condition = {
                    "$match": {
                        "uid": {"$nin": temp}, "state": {"$in": [2, 5]},
                        "type": type, "$or": [{"recommend": 1}, {"user_id": {"$in": recomm_author}}],
                    }
                }
            else:
                condition = {
                    "$match": {
                        "type": type, "recommend": 1, "uid": {"$nin": temp},
                        "state": {"$in": [2, 5]}
                    }
                }
            sort = {"$sort": SON([("create_time", -1)])}
            skip = {"$skip": 0}
            remaining_list, error = lists.queryWorksList(condition, sort, user_id, skip, 10 - len(works_list))
            if error:
                raise Exception(error)
            works_list += remaining_list
        return response(data=works_list)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def get_copyright():
    """版权说明"""
    try:
        doc = client["document"].find_one({"type": "copyright"})
        return response(data=doc["content"])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)


def get_version_number():
    """
    获取APP版本
    """
    try:
        data, error = lists.appVersion()
        if error:
            raise Exception(error)
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error：%s." % str(e), status=1, code=500)


def getToken():
    """对外获取token接口"""
    from comm.image_upload.image import ImageUpload
    token, err = ImageUpload.userLoin()
    return response(data=token, msg=err)


def getAuditStatus():
    state = lists.getAuditStatus()
    return response(data=state)


def putAuditStatus():
    state = request.json.get("state")
    if state not in [0, 1]:
        return response(msg="state invalid", code=1, status=400)
    lists.putAuditStatus(state)
    return response()
