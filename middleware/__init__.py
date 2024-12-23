from flask import Flask
from middleware.login import init_login


def init_middleware(app: Flask):
    """
    初始化中间件
    :param app:
    :return:
    """
    init_login(app)