from flask import jsonify, request
import tensorflow as tf
import numpy as np
import base64
import io
from PIL import Image

def init_predict_route(app, model, class_translations, default_class_names, img_size, default_lang):
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