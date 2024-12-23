from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # 初始化数据库对象


def init_db(app: Flask):
    # 设置数据库连接信息
    # 设置数据库连接信息，使用 SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # 使用 SQLite，数据库文件为当前目录下的 app.db
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 禁用对模型修改的监
    db.init_app(app)