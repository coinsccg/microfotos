# -*- coding: utf-8 -*-
"""
@Time: 2020/12/24 14:26
@Auth: money
@File: __init__.py.py
"""

from upload.celery_task.main import app
from upload.thread_pool.thread_pool import runAtlas, runVideo


@app.task
def microfotosWorksDataSync(args):
    runAtlas()


@app.task
def microfotosVideoWorksDataSync(args):
    runVideo()
