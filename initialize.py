# -*- coding: utf-8 -*-
"""
@Time: 2020-11-13 16:12:11
@File: initialize
@Auth: money
"""
import os
import pymongo
from utils import util
from dateutil import parser  # pip3  install python-dateutil
from flask import Flask
from flask_cors import CORS
from constant.constant import CONN_ADDR1
from constant.constant import CONN_ADDR2
from constant.constant import REPLICAT_SET
from constant.constant import USERNAME
from constant.constant import PASSWORD

log = None
client = None
stopword = None
init_stamp = None


def create_app():
    # APP应用
    app = Flask(__name__)

    # 允许跨域
    CORS(app, supports_credentials=True)

    # 允许输出中文
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

    # 生成密钥 base64.b64encode(os.urandom(64)).decode()
    # SECRET_KEY = "p7nHRvtLdwW07sQBoh/p9EBmHXv9DAcutk2vlj4MdSPNgFeTobUVJ3Ss\
    # 2Wwl3T3tuv/ctTpPw+nQKMafU3MRJQ=="
    # app.secret_key = SECRET_KEY

    # 允许上传的文件类型
    # ALLOWED_EXTENSIONS = ["txt", "pdf", "png", "jpg", "jpeg", "gif", "mp3", 
    # \"svg", "avi", "mov", "rmvb", "rm", "flv", "mp4", "3gp", "asf", "asx"]

    global log
    global client
    global init_stamp
    global stopword

    # 创建日志
    log = util.Logger("log_debug")
    log.info("The application has started.")

    # 本地数据库连接
    mongo = util.MongoDB(log)
    client = mongo.client["local_writer"]["microfigure"]

    # # 云数据库链接
    # client = pymongo.MongoClient([CONN_ADDR1, CONN_ADDR2], replicaSet=REPLICAT_SET)
    # # 管理员授权
    # client.admin.authenticate(USERNAME, PASSWORD)
    # client = client["microfigure"]

    # 时间戳起始时间
    init_date = "1970-01-01T08:00:00Z"
    # python 没有IOSDate类型 需要借助parser.parse来转 # pip3  install python-dateutil 
    init_stamp = parser.parse(init_date)

    # 加载分词词库
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    stopword_file = os.path.join(BASE_DIR, "stopword.txt")
    with open(stopword_file, "r", encoding="utf-8") as file:
        stopword = set(line.strip("\r\n") for line in file.readlines())

    # 蓝图注册
    from controller.apps.login import route as apps_login
    from controller.apps.list import route as apps_list
    from controller.apps.user import route as apps_user
    from controller.apps.works import route as apps_works
    from controller.apps.order import route as apps_order

    from controller.admin.index import route as admin_index
    from controller.admin.login import route as admin_login
    from controller.admin.finance import route as admin_finance
    from controller.admin.front import route as admin_front
    from controller.admin.operate import route as admin_operate
    from controller.admin.opinion import route as admin_opinion
    from controller.admin.system import route as admin_system
    from controller.admin.works import route as admin_works
    from controller.admin.user import route as admin_user

    # app
    app.register_blueprint(apps_login.apps_login)
    app.register_blueprint(apps_list.apps_list)
    app.register_blueprint(apps_user.apps_user)
    app.register_blueprint(apps_works.apps_works)
    app.register_blueprint(apps_order.apps_order)

    # 后台
    app.register_blueprint(admin_index.admin_index)
    app.register_blueprint(admin_login.admin_login)
    app.register_blueprint(admin_finance.admin_finance)
    app.register_blueprint(admin_front.admin_front)
    app.register_blueprint(admin_operate.admin_operate)
    app.register_blueprint(admin_opinion.admin_opinion)
    app.register_blueprint(admin_system.admin_system)
    app.register_blueprint(admin_works.admin_works)
    app.register_blueprint(admin_user.admin_user)

    return app
