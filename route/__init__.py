from flask import Flask
from route.user import bp_user
from route.dormitory import bp_dormitory
from route.roommate import bp_roommate
from route.apply import bp_apply


def init_routes(app: Flask):
    """-
    初始化路由
    :param app:
    :return:
    """
    app.register_blueprint(bp_user)
    app.register_blueprint(bp_dormitory)
    app.register_blueprint(bp_roommate)
    app.register_blueprint(bp_apply)
