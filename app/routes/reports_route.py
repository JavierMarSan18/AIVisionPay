from flask import render_template

def init_reports_route(app):
    @app.route("/reports")
    def reports():
        return render_template("reports.html")
