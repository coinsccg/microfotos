# -*- coding: utf-8 -*-
"""
@Time: 2020-11-13 16:12:11
@File: manage
@Auth: money
"""
from initialize import create_app

app = create_app()


@app.after_request
def response_headers(response):
    """处理跨域问题"""

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    response.headers["Content-Struct-Type"] = "HotAppServerApi"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
