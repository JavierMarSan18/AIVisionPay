from flask import Flask, send_from_directory
from .routes.index_route import init_index_route
from .routes.predict_route import init_predict_route
from .routes.reports_route import init_reports_route

def create_app(config):
    app = Flask(__name__)

    # Modelo y clases
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    import json

    model = load_model(config["model_path"])

    with open(config["classes_path"], "r", encoding="utf-8") as f:
        classes = json.load(f)
    class_translations = [c["class"]["translations"] for c in classes]
    class_translations = class_translations[::-1]
    default_class_names = [c["class"]["name"] for c in classes]
    default_class_names = default_class_names[::-1]

    print(default_class_names)

    # Registro de rutas
    init_index_route(app)
    init_predict_route(app, model, class_translations, default_class_names, tuple(config["image_size"]), config["default_language"])
    init_reports_route(app)

    @app.route("/reports/<path:filename>")
    def serve_reports(filename):
        return send_from_directory("../reports", filename)

    return app
