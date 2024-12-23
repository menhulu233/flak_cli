import os
from flask import Flask, render_template
from middleware import init_middleware
from model import init_db
from route import init_routes

app = Flask(__name__, static_folder="static")
app.template_folder = os.path.join(os.path.dirname(__file__), "templates")
app.config["SECRET_KEY"] = 'secret_key'


def init():
    init_routes(app)
    init_middleware(app)
    init_db(app)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == '__main__':
    app.run(port=5000, debug=True)
