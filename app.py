from flask import Flask, request, jsonify, render_template
import tensorflow as tf
import numpy as np
import base64
import io
from PIL import Image

app = Flask(__name__)

model = tf.keras.models.load_model("iavisionpay_model.keras")
class_names = ["hammer", "screwdriver", "wrench"]
img_size = (224, 224)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if "image" not in data:
        return jsonify({"error": "Falta la imagen"}), 400

    image_data = base64.b64decode(data["image"])
    image = Image.open(io.BytesIO(image_data)).resize(img_size)
    image_array = tf.keras.applications.mobilenet_v2.preprocess_input(np.array(image))
    image_array = np.expand_dims(image_array, axis=0)

    predictions = model.predict(image_array)
    predicted_index = np.argmax(predictions[0])
    confidence = float(predictions[0][predicted_index])
    predicted_label = class_names[predicted_index]

    return jsonify({
        "label": predicted_label,
        "confidence": confidence
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
