from flask import render_template

def init_index_route(app):
    @app.route("/")
    def index():
        return render_template("index.html")