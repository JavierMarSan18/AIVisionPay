import argparse
from flask import Flask, request, jsonify, render_template
import tensorflow as tf
import numpy as np
import base64
import io
from PIL import Image
import json
import os


parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Path to config JSON")
args = parser.parse_args()

# Load config
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

model = tf.keras.models.load_model(model_path)
clases = load_classes_from_json(classes_path)
class_translations = [c["class"]["translations"] for c in clases]
default_class_names = [c["class"]["name"] for c in clases]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if "image" not in data:
        return jsonify({"error": "Missing image"}), 400

    lang = data.get("lang", default_lang)

    image_data = base64.b64decode(data["image"])
    image = Image.open(io.BytesIO(image_data)).resize(img_size)
    image_array = tf.keras.applications.mobilenet_v2.preprocess_input(np.array(image))
    image_array = np.expand_dims(image_array, axis=0)

    predictions = model.predict(image_array)
    predicted_index = np.argmax(predictions[0])
    confidence = float(predictions[0][predicted_index])

    translations = class_translations[predicted_index]
    predicted_label = translations.get(lang, default_class_names[predicted_index])

    return jsonify({
        "label": predicted_label,
        "confidence": confidence,
        "language": lang
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
