import argparse
from flask import Flask
import tensorflow as tf
import json
from routes.index_route import init_index_route
from routes.predict_route import init_predict_route

# Configuración inicial (igual que antes)
parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Path to config JSON")
args = parser.parse_args()

with open(args.config, "r", encoding="utf-8") as f:
    api_config = json.load(f)

model_path = api_config["model_path"]
classes_path = api_config["classes_path"]
img_size = tuple(api_config["image_size"])
default_lang = api_config["default_language"]

def load_classes_from_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

app = Flask(__name__)

# Cargar modelos y configuraciones
model = tf.keras.models.load_model(model_path)
clases = load_classes_from_json(classes_path)
class_translations = [c["class"]["translations"] for c in clases]
default_class_names = [c["class"]["name"] for c in clases]

# Inicializar rutas
init_index_route(app)
init_predict_route(app, model, class_translations, default_class_names, img_size, default_lang)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)