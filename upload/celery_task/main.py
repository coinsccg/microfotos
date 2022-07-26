# -*- coding: utf-8 -*-
"""
@Time: 2020/12/24 14:17
@Auth: money
@File: main.py
"""
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab

# broker = 'redis://127.0.0.1:6379/1'
broker = 'redis://:gli123456@127.0.0.1:6379/1' # 密码认证


include = ['upload.celery_task.cron']

app = Celery('tasks', broker=broker, include=include)

app.conf.timezone = 'Asia/Shanghai'
app.conf.enable_utc = False
app.conf.beat_schedule = {
    # 任务一
    'every-day': {
        # 任务函数
        'task': 'upload.celery_task.cron.microfotosWorksDataSync',  # 图集定时任务
        # 传递参数
        'schedule': crontab(minute=0, hour=0),  # crontab(minute=0, hour=0) 每天凌晨执行
        'args': ('atlas',)
    },
    # 任务二
    'every-day-1-point': {
        # 任务函数
        'task': 'upload.celery_task.cron.microfotosVideoWorksDataSync',  # 影集定时任务
        # 传递参数
        'schedule': crontab(minute=0, hour='1'),  # crontab(minute=0, hour='1') 每天凌晨1点执行 crontab(minute=0, hour='1')
        'args': ('video',)
    },
}

# win(需要在虚拟环境中执行)
# 发布任务： celery -A celery_task.main beat
# 执行任务： celery -A celery_task.main worker -l info -P eventlet

# linux(需要在虚拟环境中执行)
# 发布任务： celery -A celery_task.main beat
# 执行任务： celery -A celery_task.main worker -l info

# 后台执行(需要在虚拟环境中执行)
# nohup celery -A upload.celery_task.main beat > logs/celery_beat.txt 2>&1 &
# nohup celery -A upload.celery_task.main worker -l info > logs/celery_log.txt 2>&1 &

